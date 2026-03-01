"use client";

import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import ReactECharts from "echarts-for-react";

import { useTopology } from "@/hooks/useAIOpsApi";

type Props = {
  keyword: string;
  enabled: boolean;
};

type LayoutMode = "layered" | "force";
type InstanceLabelMode = "compact" | "full" | "hover";
type NodeKind = "EC2Instance" | "Subnet" | "VPC" | "Region" | "Environment" | "Unknown";

type TopologyNode = {
  id: string;
  label: string;
  kind: NodeKind;
  degree: number;
  rank: number;
};

type TopologyEdge = { id: string; source: string; target: string; type: string };

const kindOrder: NodeKind[] = ["Region", "VPC", "Subnet", "Environment", "EC2Instance", "Unknown"];
const kindColor: Record<NodeKind, string> = {
  Region: "#26C6DA",
  VPC: "#42A5F5",
  Subnet: "#7E57C2",
  Environment: "#FFB74D",
  EC2Instance: "#8BC34A",
  Unknown: "#B0BEC5",
};
const kindSymbolSize: Record<NodeKind, number> = {
  Region: 48,
  VPC: 42,
  Subnet: 34,
  Environment: 32,
  EC2Instance: 24,
  Unknown: 24,
};

function shortLabel(text: string, max = 26): string {
  if (text.length <= max) return text;
  return `${text.slice(0, Math.floor(max / 2) - 1)}...${text.slice(-(Math.floor(max / 2) - 2))}`;
}

function inferKindFromLabel(label: string): NodeKind {
  const v = label.toLowerCase();
  if (v.includes("subnet")) return "Subnet";
  if (v.includes("vpc")) return "VPC";
  if (v.includes("region") || v.startsWith("us-") || v.startsWith("eu-") || v.startsWith("ap-")) return "Region";
  if (v.includes("prod") || v.includes("stage") || v.includes("env")) return "Environment";
  if (v.includes("airflow") || v.includes("ec2") || v.includes("instance")) return "EC2Instance";
  return "Unknown";
}

function buildTopologyModel(
  nodes: Array<{ id: string; label: string }>,
  edges: Array<{ id: string; source: string; target: string; type: string }>,
): { nodes: TopologyNode[]; edges: TopologyEdge[] } {
  const byId = new Map<string, TopologyNode>();
  for (const n of nodes || []) {
    byId.set(n.id, {
      id: n.id,
      label: n.label || n.id,
      kind: inferKindFromLabel(n.label || n.id),
      degree: 0,
      rank: 9999,
    });
  }

  const typedEdges: TopologyEdge[] = [];
  for (const e of edges || []) {
    typedEdges.push({ id: e.id, source: e.source, target: e.target, type: e.type });
    const src = byId.get(e.source);
    const tgt = byId.get(e.target);
    if (src) src.degree += 1;
    if (tgt) tgt.degree += 1;

    if (e.type === "BELONGS_TO") {
      if (src) src.kind = "EC2Instance";
      if (tgt) tgt.kind = "Subnet";
    } else if (e.type === "RUNS_IN") {
      if (src) src.kind = "EC2Instance";
      if (tgt) tgt.kind = "Environment";
    } else if (e.type === "PART_OF") {
      if (src) src.kind = "Subnet";
      if (tgt) tgt.kind = "VPC";
    } else if (e.type === "LOCATED_IN") {
      if (src) src.kind = "VPC";
      if (tgt) tgt.kind = "Region";
    }
  }

  const ranked = [...byId.values()].sort((a, b) => b.degree - a.degree);
  ranked.forEach((node, idx) => {
    node.rank = idx + 1;
  });
  return { nodes: ranked, edges: typedEdges };
}

function buildLayeredCoordinates(nodes: TopologyNode[]) {
  const grouped = new Map<NodeKind, TopologyNode[]>();
  for (const kind of kindOrder) grouped.set(kind, []);
  for (const n of nodes) {
    grouped.get(n.kind)?.push(n);
  }

  for (const [kind, list] of grouped.entries()) {
    list.sort((a, b) => a.label.localeCompare(b.label));
    grouped.set(kind, list);
  }

  const maxColumn = Math.max(...Array.from(grouped.values()).map((x) => x.length), 1);
  const canvasHeight = Math.max(760, 150 + maxColumn * 38);
  const canvasWidth = 1680;
  const leftPad = 130;
  const colGap = 260;

  const positions = new Map<string, { x: number; y: number }>();

  for (let kindIdx = 0; kindIdx < kindOrder.length; kindIdx += 1) {
    const kind = kindOrder[kindIdx];
    const list = grouped.get(kind) || [];
    if (!list.length) continue;

    if (kind === "EC2Instance" && list.length > 18) {
      const subCols = Math.min(3, Math.ceil(list.length / 18));
      const rowsPerCol = Math.ceil(list.length / subCols);
      for (let i = 0; i < list.length; i += 1) {
        const col = Math.floor(i / rowsPerCol);
        const row = i % rowsPerCol;
        const yStep = (canvasHeight - 140) / (rowsPerCol + 1);
        positions.set(list[i].id, {
          x: leftPad + kindIdx * colGap + col * 84,
          y: 70 + (row + 1) * yStep,
        });
      }
      continue;
    }

    const yStep = (canvasHeight - 140) / (list.length + 1);
    for (let i = 0; i < list.length; i += 1) {
      positions.set(list[i].id, {
        x: leftPad + kindIdx * colGap,
        y: 70 + (i + 1) * yStep,
      });
    }
  }

  return { positions, canvasHeight, canvasWidth };
}

function edgeColor(edgeType: string): string {
  if (edgeType === "BELONGS_TO") return "rgba(139,195,74,0.60)";
  if (edgeType === "RUNS_IN") return "rgba(255,183,77,0.58)";
  if (edgeType === "PART_OF") return "rgba(126,87,194,0.58)";
  if (edgeType === "LOCATED_IN") return "rgba(38,198,218,0.58)";
  return "rgba(176,190,197,0.5)";
}

export function TopologyModule({ keyword, enabled }: Props) {
  const [regionInput, setRegionInput] = useState("");
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("layered");
  const [instanceLabelMode, setInstanceLabelMode] = useState<InstanceLabelMode>("compact");
  const [showEdgeLabels, setShowEdgeLabels] = useState(false);
  const regions = useMemo(
    () => regionInput.split(",").map((x) => x.trim()).filter(Boolean),
    [regionInput],
  );

  const query = useTopology(keyword, regions, enabled);
  const topology = useMemo(
    () => buildTopologyModel(query.data?.nodes || [], query.data?.edges || []),
    [query.data?.nodes, query.data?.edges],
  );
  const layered = useMemo(() => buildLayeredCoordinates(topology.nodes), [topology.nodes]);

  const option = useMemo(() => {
    const categories = kindOrder.map((kind) => ({ name: kind }));
    const kindIndex = new Map<NodeKind, number>();
    kindOrder.forEach((k, i) => kindIndex.set(k, i));

    const graphNodes = topology.nodes.map((node) => {
      const showInstanceLabel =
        node.kind !== "EC2Instance" ||
        instanceLabelMode === "full" ||
        (instanceLabelMode === "compact" && node.rank <= 12);
      const pos = layered.positions.get(node.id);

      return {
        id: node.id,
        name: node.label,
        value: node.degree,
        category: kindIndex.get(node.kind) ?? kindIndex.get("Unknown"),
        symbolSize: kindSymbolSize[node.kind] + Math.min(16, Math.round(node.degree * 1.6)),
        x: layoutMode === "layered" ? pos?.x : undefined,
        y: layoutMode === "layered" ? pos?.y : undefined,
        itemStyle: {
          color: kindColor[node.kind],
          borderColor: "rgba(7,12,20,0.86)",
          borderWidth: 1.2,
        },
        label: {
          show: showInstanceLabel,
          position: "right",
          color: "#E6EEF7",
          fontSize: 10.5,
          formatter: shortLabel(node.label, 26),
        },
      };
    });

    const graphEdges = topology.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      value: edge.type,
      lineStyle: {
        width: 1.3,
        opacity: 0.62,
        curveness: layoutMode === "layered" ? 0.06 : 0.18,
        color: edgeColor(edge.type),
      },
      label: {
        show: showEdgeLabels,
        formatter: edge.type,
        color: "#B0BEC5",
        fontSize: 9,
      },
    }));

    return {
      backgroundColor: "transparent",
      animationDuration: 600,
      legend: [
        {
          top: 4,
          left: 6,
          icon: "circle",
          itemWidth: 10,
          itemHeight: 10,
          textStyle: { color: "#CFD8DC" },
          data: categories.map((c) => c.name),
        },
      ],
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(7,12,20,0.95)",
        borderColor: "rgba(144,202,249,0.35)",
        formatter: (params: unknown) => {
          const p = params as {
            dataType?: string;
            data?: { name?: string; value?: number };
            value?: string | number;
          };
          if (p?.dataType === "edge") {
            return `Relationship: ${String(p.value || "unknown")}`;
          }
          const n = p?.data || {};
          return [`Node: ${String(n.name || "unknown")}`, `Connections: ${Number(n.value || 0)}`].join("<br/>");
        },
      },
      series: [
        {
          type: "graph",
          layout: layoutMode === "layered" ? "none" : "force",
          roam: true,
          draggable: true,
          data: graphNodes,
          links: graphEdges,
          categories,
          edgeLabel: {
            show: showEdgeLabels,
            formatter: "{c}",
          },
          label: {
            show: true,
          },
          force:
            layoutMode === "force"
              ? {
                  repulsion: 700,
                  gravity: 0.06,
                  edgeLength: [120, 280],
                  friction: 0.25,
                }
              : undefined,
          emphasis: {
            focus: "adjacency",
            lineStyle: { width: 2.4, opacity: 0.92 },
            label: {
              show: true,
              color: "#FFFFFF",
              fontSize: 11,
            },
            edgeLabel: {
              show: true,
              formatter: "{c}",
              color: "#E0E0E0",
            },
          },
          left: 4,
          top: 30,
          right: 4,
          bottom: 8,
        },
      ],
      graphic:
        layoutMode === "layered"
          ? [
              {
                type: "text",
                left: 18,
                top: 36,
                style: { text: "Region", fill: "#26C6DA", fontSize: 11, fontWeight: 600 },
              },
              {
                type: "text",
                left: 278,
                top: 36,
                style: { text: "VPC", fill: "#42A5F5", fontSize: 11, fontWeight: 600 },
              },
              {
                type: "text",
                left: 538,
                top: 36,
                style: { text: "Subnet", fill: "#7E57C2", fontSize: 11, fontWeight: 600 },
              },
              {
                type: "text",
                left: 798,
                top: 36,
                style: { text: "Environment", fill: "#FFB74D", fontSize: 11, fontWeight: 600 },
              },
              {
                type: "text",
                left: 1062,
                top: 36,
                style: { text: "EC2 Instance", fill: "#8BC34A", fontSize: 11, fontWeight: 600 },
              },
            ]
          : [],
    };
  }, [instanceLabelMode, layered.positions, layoutMode, showEdgeLabels, topology.edges, topology.nodes]);

  if (!enabled) return <Alert severity="info">Provide a keyword first.</Alert>;
  if (query.isLoading) return <CircularProgress />;
  if (query.isError || !query.data) return <Alert severity="error">Failed to load topology.</Alert>;

  const data = query.data;

  return (
    <Card>
      <CardContent>
        <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 2, alignItems: { lg: "center" } }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: "wrap" }}>
            <Typography variant="h6">Topology Explorer</Typography>
            <Chip label={`Nodes: ${data.stats.nodes ?? 0}`} />
            <Chip label={`Edges: ${data.stats.edges ?? 0}`} />
            <Chip label={`Instances: ${data.stats.instances ?? 0}`} />
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.2} sx={{ flexGrow: 1 }}>
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel id="layout-mode-label">Layout</InputLabel>
              <Select
                labelId="layout-mode-label"
                value={layoutMode}
                label="Layout"
                onChange={(e) => setLayoutMode(e.target.value as LayoutMode)}
              >
                <MenuItem value="layered">Layered (recommended)</MenuItem>
                <MenuItem value="force">Force-directed</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="instance-label-mode-label">Instance labels</InputLabel>
              <Select
                labelId="instance-label-mode-label"
                value={instanceLabelMode}
                label="Instance labels"
                onChange={(e) => setInstanceLabelMode(e.target.value as InstanceLabelMode)}
              >
                <MenuItem value="compact">Compact (top connected)</MenuItem>
                <MenuItem value="full">All instance labels</MenuItem>
                <MenuItem value="hover">Hover only</MenuItem>
              </Select>
            </FormControl>
            <Stack direction="row" alignItems="center" sx={{ px: 1 }}>
              <Switch checked={showEdgeLabels} onChange={(e) => setShowEdgeLabels(e.target.checked)} />
              <Typography variant="body2" sx={{ opacity: 0.85 }}>
                Show relationship labels
              </Typography>
            </Stack>
          </Stack>
        </Stack>
        <TextField
          fullWidth
          label="Region filters (comma separated)"
          value={regionInput}
          onChange={(e) => setRegionInput(e.target.value)}
          helperText="Example: us-west-2,us-east-1"
          sx={{ mb: 2 }}
        />
        <Box
          sx={{
            borderRadius: 2,
            border: "1px solid rgba(148,163,184,0.20)",
            p: 1,
            background: "linear-gradient(130deg, rgba(15,23,42,0.95) 0%, rgba(8,47,73,0.60) 100%)",
          }}
        >
          <ReactECharts
            option={option}
            style={{ height: Math.max(680, layered.canvasHeight), width: "100%" }}
            opts={{ renderer: "canvas" }}
          />
        </Box>
      </CardContent>
    </Card>
  );
}

