"use client";

import { useMemo, useState } from "react";
import { Alert, Card, CardContent, Chip, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import ReactECharts from "echarts-for-react";

import { useTopology } from "@/hooks/useAIOpsApi";

type Props = {
  keyword: string;
  enabled: boolean;
};

export function TopologyModule({ keyword, enabled }: Props) {
  const [regionInput, setRegionInput] = useState("");
  const regions = useMemo(
    () => regionInput.split(",").map((x) => x.trim()).filter(Boolean),
    [regionInput],
  );

  const query = useTopology(keyword, regions, enabled);

  if (!enabled) return <Alert severity="info">Provide a keyword first.</Alert>;
  if (query.isLoading) return <CircularProgress />;
  if (query.isError || !query.data) return <Alert severity="error">Failed to load topology.</Alert>;

  const data = query.data;
  const option = {
    backgroundColor: "transparent",
    tooltip: {},
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        data: data.nodes.map((n) => ({
          id: n.id,
          name: n.label,
          value: n.label,
          symbolSize: 16,
        })),
        links: data.edges.map((e) => ({
          source: e.source,
          target: e.target,
          lineStyle: { width: 1.5 },
          label: { show: true, formatter: e.type },
        })),
        label: { show: true, color: "#E3F2FD" },
        force: { repulsion: 180, edgeLength: [80, 180] },
      },
    ],
  };

  return (
    <Card>
      <CardContent>
        <Stack direction="row" spacing={2} sx={{ mb: 2, alignItems: "center" }}>
          <Typography variant="h6">Topology Explorer</Typography>
          <Chip label={`Nodes: ${data.stats.nodes ?? 0}`} />
          <Chip label={`Edges: ${data.stats.edges ?? 0}`} />
          <Chip label={`Instances: ${data.stats.instances ?? 0}`} />
        </Stack>
        <TextField
          fullWidth
          label="Region filters (comma separated)"
          value={regionInput}
          onChange={(e) => setRegionInput(e.target.value)}
          helperText="Example: us-west-2,us-east-1"
          sx={{ mb: 2 }}
        />
        <ReactECharts option={option} style={{ height: 520, width: "100%" }} />
      </CardContent>
    </Card>
  );
}

