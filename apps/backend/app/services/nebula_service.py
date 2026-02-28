from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool

from app.core.config import get_settings


def _as_str(x: Any) -> str:
    try:
        if isinstance(x, bytes):
            s = x.decode("utf-8", errors="ignore")
        else:
            s = str(x)
        s = s.strip()
        if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
            s = s[1:-1].strip()
        return s
    except Exception:
        return str(x)


@dataclass
class NebulaSession:
    pool: ConnectionPool
    session: Any


class NebulaService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def create_session(self) -> NebulaSession:
        config = Config()
        config.max_connection_pool_size = 10
        pool = ConnectionPool()
        ok = pool.init([(self.settings.nebula_host, self.settings.nebula_port)], config)
        if not ok:
            raise RuntimeError("Failed to initialize Nebula connection pool")

        session = pool.get_session(self.settings.nebula_user, self.settings.nebula_password)
        resp = session.execute(f"USE {self.settings.nebula_space}")
        if not resp.is_succeeded():
            session.release()
            pool.close()
            raise RuntimeError(f"Failed to use space '{self.settings.nebula_space}': {resp.error_msg()}")
        return NebulaSession(pool=pool, session=session)

    def fetch_all_edges(self) -> pd.DataFrame:
        ns = self.create_session()
        try:
            queries = [
                ("BELONGS_TO", f"MATCH (i:EC2Instance)-[:BELONGS_TO]->(s:Subnet) RETURN id(i) AS src, id(s) AS tgt LIMIT {self.settings.nebula_edge_limit}"),
                ("RUNS_IN", f"MATCH (i:EC2Instance)-[:RUNS_IN]->(e:Environment) RETURN id(i) AS src, id(e) AS tgt LIMIT {self.settings.nebula_edge_limit}"),
                ("PART_OF", f"MATCH (s:Subnet)-[:PART_OF]->(v:VPC) RETURN id(s) AS src, id(v) AS tgt LIMIT {self.settings.nebula_edge_limit}"),
                ("LOCATED_IN", f"MATCH (v:VPC)-[:LOCATED_IN]->(r:Region) RETURN id(v) AS src, id(r) AS tgt LIMIT {self.settings.nebula_edge_limit}"),
            ]
            rows: list[dict[str, str]] = []
            for edge_type, query in queries:
                result = ns.session.execute(query)
                if not result.is_succeeded():
                    continue
                srcs = result.column_values("src")
                tgts = result.column_values("tgt")
                for src, tgt in zip(srcs, tgts):
                    rows.append({"source": _as_str(src), "target": _as_str(tgt), "edge_type": edge_type})
            return pd.DataFrame(rows)
        finally:
            ns.session.release()
            ns.pool.close()

    @staticmethod
    def hierarchical_filter(
        df: pd.DataFrame,
        *,
        instance_filter: list[str] | None = None,
        region_filter: list[str] | None = None,
        application_filter: list[str] | None = None,
    ) -> pd.DataFrame:
        instance_filter = instance_filter or []
        region_filter = region_filter or []
        application_filter = application_filter or []
        if df.empty:
            return df

        all_instances = df[df["edge_type"] == "BELONGS_TO"]["source"].unique()
        if application_filter:
            app_instances = [
                inst for inst in all_instances if any(app.lower() in str(inst).lower() for app in application_filter)
            ]
        else:
            app_instances = list(all_instances)

        if region_filter:
            vpcs_in_region = df[(df["edge_type"] == "LOCATED_IN") & (df["target"].isin(region_filter))]["source"].unique()
            subnets_in_region = df[(df["edge_type"] == "PART_OF") & (df["target"].isin(vpcs_in_region))]["source"].unique()
            instances_in_region = df[(df["edge_type"] == "BELONGS_TO") & (df["target"].isin(subnets_in_region))]["source"].unique()
        else:
            instances_in_region = app_instances

        if instance_filter:
            selected_instances = [i for i in instance_filter if i in app_instances and i in instances_in_region]
        else:
            selected_instances = [i for i in app_instances if i in instances_in_region]
        if not selected_instances:
            return pd.DataFrame(columns=df.columns)

        belongs = df[(df["edge_type"] == "BELONGS_TO") & (df["source"].isin(selected_instances))]
        subnets = belongs["target"].unique()
        part_of = df[(df["edge_type"] == "PART_OF") & (df["source"].isin(subnets))]
        vpcs = part_of["target"].unique()
        located = df[(df["edge_type"] == "LOCATED_IN") & (df["source"].isin(vpcs))]
        if region_filter:
            located = located[located["target"].isin(region_filter)]
        runs_in = df[(df["edge_type"] == "RUNS_IN") & (df["source"].isin(selected_instances))]
        return pd.concat([belongs, part_of, located, runs_in], ignore_index=True).drop_duplicates()

    def topology_for_keyword(self, keyword: str, region_filter: list[str] | None = None) -> dict[str, Any]:
        df = self.fetch_all_edges()
        if df.empty:
            return {"nodes": [], "edges": [], "stats": {"nodes": 0, "edges": 0, "instances": 0}}
        filtered = self.hierarchical_filter(
            df,
            instance_filter=[],
            region_filter=region_filter or [],
            application_filter=[keyword] if keyword else [],
        )
        if filtered.empty:
            return {"nodes": [], "edges": [], "stats": {"nodes": 0, "edges": 0, "instances": 0}}

        node_values = pd.concat([filtered["source"].astype(str), filtered["target"].astype(str)]).unique()
        nodes = [{"id": n, "label": n} for n in sorted(node_values)]
        edges = [
            {"id": f"{r['edge_type']}:{r['source']}->{r['target']}", "source": r["source"], "target": r["target"], "type": r["edge_type"]}
            for _, r in filtered.iterrows()
        ]
        instances = filtered[filtered["edge_type"] == "BELONGS_TO"]["source"].nunique()
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "nodes": int(len(nodes)),
                "edges": int(len(edges)),
                "instances": int(instances),
            },
        }

