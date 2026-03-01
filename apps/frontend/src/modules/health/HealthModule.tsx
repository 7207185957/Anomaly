"use client";

import { Alert, Card, CardContent, CircularProgress, Grid, Typography } from "@mui/material";
import ReactECharts from "echarts-for-react";

import { useClusterHealth } from "@/hooks/useAIOpsApi";
import { TimeWindowPayload } from "@/types/api";

type Props = {
  payload: TimeWindowPayload;
  enabled: boolean;
};

type TimelineRow = {
  minute?: string;
  health?: number;
  failure?: number;
  risk?: number;
  infra_anomalies?: number;
  app_anomalies?: number;
  app_log_errors?: number;
  dag_log_errors?: number;
  total_events?: number;
  health_archetype?: string;
  health_sequence?: string;
};

type AssetRow = {
  asset_id?: string;
  minute?: string;
  health_score?: number;
  impact_total?: number;
  host_ip?: string;
  app_log_errors?: number;
  dag_log_errors?: number;
  contributors?: Array<{ metric?: string; value?: number; severity?: string; count?: number }>;
};

type TooltipAxisParam = {
  dataIndex?: number;
  axisValue?: string | number;
  axisValueLabel?: string;
  seriesName?: string;
  data?: number;
};

function fmtContributors(row: AssetRow): string {
  const cs = Array.isArray(row.contributors) ? row.contributors : [];
  if (!cs.length) return "none";
  return cs
    .slice(0, 3)
    .map((c) => `${c.metric || "metric"}=${c.value ?? "?"} (${c.severity || "n/a"}, x${c.count ?? 1})`)
    .join(" | ");
}

function buildHealthOption(rows: TimelineRow[], title: string) {
  const x = rows.map((r) => r.minute || "");
  const health = rows.map((r) => Number(r.health ?? 0));
  const failure = rows.map((r) => Number(r.failure ?? 0));
  const risk = rows.map((r) => Number(r.risk ?? 0));

  return {
    backgroundColor: "transparent",
    title: { text: title, textStyle: { color: "#CFD8DC", fontSize: 14 } },
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown) => {
        const arr = (Array.isArray(params) ? params : []) as TooltipAxisParam[];
        const idx = arr.length ? Number(arr[0].dataIndex ?? 0) : 0;
        const r = rows[idx] || {};
        return [
          `time=${r.minute || "n/a"}`,
          `health=${Number(r.health ?? 0).toFixed(1)}`,
          `failure=${Number(r.failure ?? 0).toFixed(1)}`,
          `risk=${Number(r.risk ?? 0).toFixed(1)}`,
          `infra_anomalies=${r.infra_anomalies ?? 0}`,
          `app_anomalies=${r.app_anomalies ?? 0}`,
          `app_log_errors=${r.app_log_errors ?? 0}`,
          `dag_log_errors=${r.dag_log_errors ?? 0}`,
          `total_events=${r.total_events ?? 0}`,
          `health_archetype=${r.health_archetype || "n/a"}`,
          `health_sequence=${r.health_sequence || "n/a"}`,
        ].join("<br/>");
      },
    },
    legend: { data: ["Health", "Failure", "Risk"], textStyle: { color: "#B0BEC5" } },
    grid: { top: 50, right: 24, bottom: 24, left: 42 },
    xAxis: {
      type: "category",
      data: x,
      axisLabel: { color: "#B0BEC5", hideOverlap: true },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { color: "#B0BEC5" },
    },
    series: [
      { name: "Health", data: health, type: "line", smooth: true },
      { name: "Failure", data: failure, type: "line", smooth: true },
      { name: "Risk", data: risk, type: "line", smooth: true },
    ],
  };
}

function buildAssetOption(rows: AssetRow[], title: string) {
  const grouped = new Map<string, AssetRow[]>();
  for (const row of rows || []) {
    const key = String(row.asset_id || "unknown");
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(row);
  }
  const series = Array.from(grouped.entries()).map(([asset, points]) => ({
    name: asset,
    type: "line",
    smooth: true,
    data: points.map((p) => Number(p.health_score ?? 0)),
    customData: points,
  }));
  const firstPoints = grouped.size ? grouped.values().next().value || [] : [];
  const x = (firstPoints as AssetRow[]).map((r) => r.minute || "");

  return {
    backgroundColor: "transparent",
    title: { text: title, textStyle: { color: "#CFD8DC", fontSize: 14 } },
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown) => {
        const arr = (Array.isArray(params) ? params : []) as TooltipAxisParam[];
        if (!arr.length) return "";
        const lines = [String(arr[0].axisValueLabel || arr[0].axisValue || "")];
        for (const p of arr) {
          const row = p.seriesName
            ? (grouped.get(p.seriesName) || [])[Number(p.dataIndex ?? 0)]
            : undefined;
          lines.push(
            `${p.seriesName || "asset"}: ${Number(p.data ?? 0).toFixed(2)} ` +
              `(impact=${Number(row?.impact_total ?? 0).toFixed(2)}, app_logs=${row?.app_log_errors ?? 0}, dag_logs=${row?.dag_log_errors ?? 0})`,
          );
          if (row) {
            lines.push(`contributors: ${fmtContributors(row)}`);
          }
        }
        return lines.join("<br/>");
      },
    },
    legend: { textStyle: { color: "#B0BEC5" } },
    grid: { top: 50, right: 24, bottom: 24, left: 42 },
    xAxis: { type: "category", data: x, axisLabel: { color: "#B0BEC5", hideOverlap: true } },
    yAxis: { type: "value", min: 0, max: 100, axisLabel: { color: "#B0BEC5" } },
    series,
  };
}

export function HealthModule({ payload, enabled }: Props) {
  const query = useClusterHealth(payload, enabled);
  if (!enabled) return <Alert severity="info">Provide a keyword to load health dashboards.</Alert>;
  if (query.isLoading) return <CircularProgress />;
  if (query.isError || !query.data) return <Alert severity="error">Failed to load health dashboards.</Alert>;
  const data = query.data;
  const combinedRows = (data.health_failure_timeline || []) as TimelineRow[];
  const infraRows = (data.infra_only?.health_failure_timeline || []) as TimelineRow[];
  const appRows = (data.app_only?.health_failure_timeline || []) as TimelineRow[];
  const combinedAsset = (data.asset_health_timeline || []) as AssetRow[];
  const infraAsset = (data.infra_only?.asset_health_timeline || []) as AssetRow[];
  const appAsset = (data.app_only?.asset_health_timeline || []) as AssetRow[];

  const optionCombined = buildHealthOption(combinedRows, "2.0 Combined cluster health deviation (Infra + App + Logs)");
  const optionInfra = buildHealthOption(infraRows, "2.1 Cluster Infra health deviation");
  const optionApp = buildHealthOption(appRows, "2.2 Cluster Application health deviation");
  const optionInfraAsset = buildAssetOption(infraAsset, "2.1 Asset timeline (Infra)");
  const optionAppAsset = buildAssetOption(appAsset, "2.2 Asset timeline (Application)");
  const optionCombinedAsset = buildAssetOption(combinedAsset, "2.0 Asset timeline (Combined)");

  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Health Score</Typography>
            <Typography variant="h4">{data.health_score ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Health State</Typography>
            <Typography variant="h6">
              {data.health_signature?.health_state || "Unknown"}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Infra Cluster Health</Typography>
            <Typography variant="h4">{Math.round(data.infra_only?.cluster_health ?? 0)}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">App Cluster Health</Typography>
            <Typography variant="h4">{Math.round(data.app_only?.cluster_health ?? 0)}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card>
          <CardContent>
            <ReactECharts option={optionCombined} style={{ height: 360, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card>
          <CardContent>
            <ReactECharts option={optionCombinedAsset} style={{ height: 300, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Card>
          <CardContent>
            <ReactECharts option={optionInfra} style={{ height: 320, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Card>
          <CardContent>
            <ReactECharts option={optionApp} style={{ height: 320, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Card>
          <CardContent>
            <ReactECharts option={optionInfraAsset} style={{ height: 300, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Card>
          <CardContent>
            <ReactECharts option={optionAppAsset} style={{ height: 300, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

