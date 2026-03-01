"use client";

import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import ReactECharts from "echarts-for-react";
import { useMemo, useState } from "react";

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

type ViewKey = "combined" | "infra" | "app";

function fmtContributors(row: AssetRow): string {
  const cs = Array.isArray(row.contributors) ? row.contributors : [];
  if (!cs.length) return "none";
  return cs
    .slice(0, 3)
    .map((c) => `${c.metric || "metric"}=${c.value ?? "?"} (${c.severity || "n/a"}, x${c.count ?? 1})`)
    .join(" | ");
}

function minuteLabel(value: string | undefined): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

function shortAssetName(value: string): string {
  if (value.length <= 28) return value;
  return `${value.slice(0, 13)}...${value.slice(-11)}`;
}

function sortAssetRows(rows: AssetRow[]): AssetRow[] {
  return [...rows].sort((a, b) => {
    const ta = new Date(a.minute || "").getTime();
    const tb = new Date(b.minute || "").getTime();
    return ta - tb;
  });
}

function buildHealthOption(rows: TimelineRow[], title: string) {
  const x = rows.map((r) => r.minute || "");
  const health = rows.map((r) => Number(r.health ?? 0));
  const failure = rows.map((r) => Number(r.failure ?? 0));
  const risk = rows.map((r) => Number(r.risk ?? 0));

  return {
    backgroundColor: "transparent",
    animationDuration: 500,
    title: { text: title, top: 6, textStyle: { color: "#CFD8DC", fontSize: 14, fontWeight: 600 } },
    tooltip: {
      trigger: "axis",
      appendToBody: true,
      confine: false,
      enterable: true,
      extraCssText: "max-width: 560px; white-space: normal; overflow-wrap:anywhere; z-index: 99999;",
      backgroundColor: "rgba(7, 12, 20, 0.95)",
      borderColor: "rgba(144, 202, 249, 0.35)",
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
    legend: {
      data: ["Health", "Failure", "Risk"],
      top: 26,
      textStyle: { color: "#B0BEC5", fontSize: 11 },
      itemWidth: 14,
      itemHeight: 8,
    },
    grid: { top: 58, right: 24, bottom: 72, left: 48 },
    dataZoom: [
      {
        type: "inside",
        start: 0,
        end: 100,
      },
      {
        type: "slider",
        bottom: 18,
        height: 18,
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#90A4AE" },
      },
    ],
    xAxis: {
      type: "category",
      data: x,
      axisLabel: { color: "#B0BEC5", hideOverlap: true, formatter: minuteLabel, margin: 12 },
      axisLine: { lineStyle: { color: "rgba(176,190,197,0.5)" } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { color: "#B0BEC5" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.10)" } },
    },
    series: [
      {
        name: "Health",
        data: health,
        type: "line",
        smooth: 0.35,
        showSymbol: false,
        lineStyle: { width: 2.5, color: "#8BC34A" },
        areaStyle: { color: "rgba(139,195,74,0.15)" },
      },
      {
        name: "Failure",
        data: failure,
        type: "line",
        smooth: 0.35,
        showSymbol: false,
        lineStyle: { width: 2, color: "#FF7043" },
      },
      {
        name: "Risk",
        data: risk,
        type: "line",
        smooth: 0.35,
        showSymbol: false,
        lineStyle: { width: 2, color: "#42A5F5" },
      },
    ],
  };
}

function buildAssetOption(rows: AssetRow[], title: string, manySeries: boolean) {
  const grouped = new Map<string, AssetRow[]>();
  for (const row of rows || []) {
    const key = String(row.asset_id || "unknown");
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(row);
  }

  for (const [asset, points] of grouped.entries()) {
    grouped.set(asset, sortAssetRows(points));
  }

  const series = Array.from(grouped.entries()).map(([asset, points]) => ({
    name: asset,
    type: "line",
    smooth: true,
    data: points.map((p) => Number(p.health_score ?? 0)),
    showSymbol: false,
    lineStyle: { width: 2 },
  }));
  const firstPoints = grouped.size ? grouped.values().next().value || [] : [];
  const x = (firstPoints as AssetRow[]).map((r) => r.minute || "");

  return {
    backgroundColor: "transparent",
    animationDuration: 500,
    title: { text: title, top: 6, textStyle: { color: "#CFD8DC", fontSize: 14, fontWeight: 600 } },
    tooltip: {
      trigger: "axis",
      appendToBody: true,
      confine: false,
      enterable: true,
      extraCssText: "max-width: 640px; white-space: normal; overflow-wrap:anywhere; z-index: 99999;",
      backgroundColor: "rgba(7, 12, 20, 0.95)",
      borderColor: "rgba(144, 202, 249, 0.35)",
      formatter: (params: unknown) => {
        const arr = (Array.isArray(params) ? params : []) as TooltipAxisParam[];
        if (!arr.length) return "";
        const lines = [`minute=${String(arr[0].axisValueLabel || arr[0].axisValue || "")}`];
        for (const p of arr) {
          const row = p.seriesName
            ? (grouped.get(p.seriesName) || [])[Number(p.dataIndex ?? 0)]
            : undefined;
          lines.push(
            `${p.seriesName || "asset"}: health=${Number(p.data ?? 0).toFixed(2)} ` +
              `(impact=${Number(row?.impact_total ?? 0).toFixed(2)}, app_logs=${row?.app_log_errors ?? 0}, dag_logs=${row?.dag_log_errors ?? 0})`,
          );
          if (row) {
            lines.push(`contributors: ${fmtContributors(row)}`);
          }
        }
        return lines.join("<br/>");
      },
    },
    legend: {
      type: "scroll",
      orient: manySeries ? "vertical" : "horizontal",
      top: manySeries ? 34 : 26,
      right: manySeries ? 8 : "auto",
      left: manySeries ? "auto" : 16,
      bottom: manySeries ? 46 : "auto",
      textStyle: { color: "#B0BEC5", fontSize: 11 },
      pageTextStyle: { color: "#90A4AE" },
      itemWidth: 14,
      itemHeight: 8,
      formatter: (name: string) => shortAssetName(name),
    },
    grid: { top: 58, right: manySeries ? 250 : 20, bottom: 72, left: 52 },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      {
        type: "slider",
        bottom: 18,
        height: 18,
        borderColor: "rgba(255,255,255,0.12)",
        textStyle: { color: "#90A4AE" },
      },
    ],
    xAxis: {
      type: "category",
      data: x,
      axisLabel: { color: "#B0BEC5", hideOverlap: true, formatter: minuteLabel, margin: 12 },
      axisLine: { lineStyle: { color: "rgba(176,190,197,0.5)" } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLabel: { color: "#B0BEC5" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.10)" } },
    },
    series,
  };
}

export function HealthModule({ payload, enabled }: Props) {
  const query = useClusterHealth(payload, enabled);
  const [view, setView] = useState<ViewKey>("combined");
  const [assetMode, setAssetMode] = useState<string>("top");
  const [topN, setTopN] = useState<number>(8);
  const data = query.data;
  const rowsByView = useMemo(
    () =>
      ({
        combined: (data?.health_failure_timeline || []) as TimelineRow[],
        infra: (data?.infra_only?.health_failure_timeline || []) as TimelineRow[],
        app: (data?.app_only?.health_failure_timeline || []) as TimelineRow[],
      }) satisfies Record<ViewKey, TimelineRow[]>,
    [data],
  );
  const assetRowsByView = useMemo(
    () =>
      ({
        combined: (data?.asset_health_timeline || []) as AssetRow[],
        infra: (data?.infra_only?.asset_health_timeline || []) as AssetRow[],
        app: (data?.app_only?.asset_health_timeline || []) as AssetRow[],
      }) satisfies Record<ViewKey, AssetRow[]>,
    [data],
  );

  const activeTimelineRows = rowsByView[view];
  const activeAssetRows = assetRowsByView[view];

  const assetRanking = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of activeAssetRows) {
      const id = String(row.asset_id || "unknown");
      const score = Number(row.health_score ?? 100);
      const curr = map.get(id);
      map.set(id, curr === undefined ? score : Math.min(curr, score));
    }
    return [...map.entries()].sort((a, b) => a[1] - b[1]).map(([id]) => id);
  }, [activeAssetRows]);

  const effectiveAssetMode = assetMode !== "top" && !assetRanking.includes(assetMode) ? "top" : assetMode;

  const visibleAssetIds = useMemo(
    () => (effectiveAssetMode === "top" ? assetRanking.slice(0, topN) : [effectiveAssetMode]),
    [effectiveAssetMode, assetRanking, topN],
  );

  const filteredAssetRows = useMemo(
    () => activeAssetRows.filter((r) => visibleAssetIds.includes(String(r.asset_id || "unknown"))),
    [activeAssetRows, visibleAssetIds],
  );

  const activeLabel = view === "combined" ? "2.0 Combined" : view === "infra" ? "2.1 Infra" : "2.2 Application";
  const healthOption = buildHealthOption(
    activeTimelineRows,
    `${activeLabel} cluster health deviation`,
  );
  const assetOption = buildAssetOption(
    filteredAssetRows,
    `${activeLabel} asset timeline`,
    visibleAssetIds.length > 7,
  );
  const assetChartHeight = Math.max(340, Math.min(520, 300 + Math.floor(visibleAssetIds.length / 4) * 30));

  if (!enabled) return <Alert severity="info">Provide a keyword to load health dashboards.</Alert>;
  if (query.isLoading) return <CircularProgress />;
  if (query.isError || !query.data) return <Alert severity="error">Failed to load health dashboards.</Alert>;
  const dashboardData = query.data;

  return (
    <Grid container spacing={2.2}>
      <Grid size={12}>
        <Card
          sx={{
            border: "1px solid rgba(148,163,184,0.18)",
            background:
              "linear-gradient(130deg, rgba(15,23,42,0.94) 0%, rgba(10,35,66,0.78) 55%, rgba(22,78,99,0.62) 100%)",
          }}
        >
          <CardContent>
            <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={1}>
              <Box>
                <Typography variant="h5">Health Intelligence Dashboard</Typography>
                <Typography variant="body2" sx={{ opacity: 0.8, mt: 0.4 }}>
                  Dynamic, non-overlapping charts with drill-down by combined / infra / application views.
                </Typography>
              </Box>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Chip label={`Scope: ${payload.keyword || "all assets"}`} color="primary" size="small" />
                <Chip label={`Assets: ${assetRanking.length}`} size="small" />
                <Chip label={`Points: ${activeTimelineRows.length}`} size="small" />
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Combined Health Score</Typography>
            <Typography variant="h4">{dashboardData.health_score ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Health State</Typography>
            <Typography variant="h6">
              {dashboardData.health_signature?.health_state || "Unknown"}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Infra Cluster Health</Typography>
            <Typography variant="h4">{Math.round(dashboardData.infra_only?.cluster_health ?? 0)}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Application Cluster Health</Typography>
            <Typography variant="h4">{Math.round(dashboardData.app_only?.cluster_health ?? 0)}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card sx={{ overflow: "visible" }}>
          <CardContent>
            <Stack
              direction={{ xs: "column", lg: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "flex-start", lg: "center" }}
              gap={1.2}
              sx={{ mb: 1 }}
            >
              <Tabs
                value={view}
                onChange={(_, value: ViewKey) => setView(value)}
                variant="scrollable"
                allowScrollButtonsMobile
              >
                <Tab value="combined" label="2.0 Combined" />
                <Tab value="infra" label="2.1 Infra" />
                <Tab value="app" label="2.2 Application" />
              </Tabs>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1} width={{ xs: "100%", lg: "auto" }}>
                <FormControl size="small" sx={{ minWidth: 140 }}>
                  <Select
                    value={String(topN)}
                    onChange={(e) => setTopN(Number(e.target.value))}
                    disabled={effectiveAssetMode !== "top"}
                  >
                    <MenuItem value="5">Top 5 assets</MenuItem>
                    <MenuItem value="8">Top 8 assets</MenuItem>
                    <MenuItem value="12">Top 12 assets</MenuItem>
                    <MenuItem value="20">Top 20 assets</MenuItem>
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 240 }}>
                  <Select value={effectiveAssetMode} onChange={(e) => setAssetMode(String(e.target.value))}>
                    <MenuItem value="top">Auto focus (worst assets)</MenuItem>
                    {assetRanking.map((assetId) => (
                      <MenuItem key={assetId} value={assetId}>
                        {assetId}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>
            </Stack>

            <ReactECharts option={healthOption} style={{ height: 390, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card sx={{ overflow: "visible" }}>
          <CardContent>
            <ReactECharts option={assetOption} style={{ height: assetChartHeight, width: "100%" }} />
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

