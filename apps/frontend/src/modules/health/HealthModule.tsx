"use client";

import { Alert, Card, CardContent, CircularProgress, Grid, Typography } from "@mui/material";
import ReactECharts from "echarts-for-react";

import { useClusterHealth } from "@/hooks/useAIOpsApi";
import { TimeWindowPayload } from "@/types/api";

type Props = {
  payload: TimeWindowPayload;
  enabled: boolean;
};

export function HealthModule({ payload, enabled }: Props) {
  const query = useClusterHealth(payload, enabled);
  if (!enabled) return <Alert severity="info">Provide a keyword to load health dashboards.</Alert>;
  if (query.isLoading) return <CircularProgress />;
  if (query.isError || !query.data) return <Alert severity="error">Failed to load health dashboards.</Alert>;

  const data = query.data;
  const series = data.health_failure_timeline || [];
  const x = series.map((row) => row.minute);
  const health = series.map((row) => Number(row.health ?? 0));
  const failure = series.map((row) => Number(row.failure ?? 0));
  const risk = series.map((row) => Number(row.risk ?? 0));

  const option = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { data: ["Health", "Failure", "Risk"] },
    grid: { top: 40, right: 24, bottom: 24, left: 42 },
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
            <Typography variant="overline">P10</Typography>
            <Typography variant="h4">{Math.round(data.health_signature?.health_p10 ?? 0)}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Last Health</Typography>
            <Typography variant="h4">{Math.round(data.health_signature?.health_last ?? 0)}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Cluster Health Timeline
            </Typography>
            <ReactECharts option={option} style={{ height: 420, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

