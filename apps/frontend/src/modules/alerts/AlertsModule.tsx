"use client";

import { useMemo, useState } from "react";
import {
  Alert,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControlLabel,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";

import { useClusterHealth } from "@/hooks/useAIOpsApi";
import { TimeWindowPayload } from "@/types/api";

type Props = {
  payload: TimeWindowPayload;
  enabled: boolean;
};

const healthyArchetypes = new Set([
  "HEALTHY_STABLE",
  "RECOVERED_STABLE",
  "MINOR_BLIP",
]);

const isAlertingRow = (row: Record<string, unknown>) => {
  const archetype = String(row.health_archetype || "").toUpperCase();
  if (archetype && !healthyArchetypes.has(archetype)) {
    return true;
  }
  const failure = Number(row.failure ?? 0);
  const risk = Number(row.risk ?? 0);
  const infra = Number(row.infra_anomalies ?? 0);
  const app = Number(row.app_anomalies ?? 0);
  const appLogs = Number(row.app_log_errors ?? 0);
  const dagLogs = Number(row.dag_log_errors ?? 0);
  return failure >= 20 || risk >= 20 || infra > 0 || app > 0 || appLogs > 0 || dagLogs > 0;
};

const alertReason = (row: Record<string, unknown>) => {
  const reasons: string[] = [];
  if (Number(row.failure ?? 0) >= 20) reasons.push("failure>=20");
  if (Number(row.risk ?? 0) >= 20) reasons.push("risk>=20");
  if (Number(row.infra_anomalies ?? 0) > 0) reasons.push("infra-anomaly");
  if (Number(row.app_anomalies ?? 0) > 0) reasons.push("app-anomaly");
  if (Number(row.app_log_errors ?? 0) > 0) reasons.push("app-log-error");
  if (Number(row.dag_log_errors ?? 0) > 0) reasons.push("dag-log-error");
  const archetype = String(row.health_archetype || "").toUpperCase();
  if (archetype && !healthyArchetypes.has(archetype)) reasons.push(archetype.toLowerCase());
  return reasons.length ? reasons.join(", ") : "informational";
};

export function AlertsModule({ payload, enabled }: Props) {
  const [onlyUnhealthy, setOnlyUnhealthy] = useState(false);
  const query = useClusterHealth(payload, enabled);

  const colDefs = useMemo<ColDef[]>(
    () => [
      { field: "minute", headerName: "Minute (UTC)", minWidth: 220, flex: 1 },
      { field: "alert_reason", headerName: "Alert Reason", minWidth: 230, flex: 1 },
      { field: "health", headerName: "Health", width: 110 },
      { field: "failure", headerName: "Failure", width: 110 },
      { field: "risk", headerName: "Risk", width: 110 },
      { field: "health_archetype", headerName: "Health Archetype", minWidth: 220, flex: 1 },
      { field: "health_sequence", headerName: "Sequence", minWidth: 220, flex: 1 },
      { field: "infra_anomalies", headerName: "Infra", width: 90 },
      { field: "app_anomalies", headerName: "App", width: 90 },
      { field: "app_log_errors", headerName: "App Logs", width: 110 },
      { field: "dag_log_errors", headerName: "DAG Logs", width: 110 },
    ],
    [],
  );

  if (!enabled) {
    return <Alert severity="info">Alerts are disabled until authentication is complete.</Alert>;
  }
  if (query.isLoading) return <CircularProgress />;
  if (query.isError || !query.data) return <Alert severity="error">Failed to load alerts.</Alert>;

  const timeline = query.data.health_failure_timeline || [];
  const alertTimeline = timeline.map((row) => ({ ...row, alert_reason: alertReason(row) }));
  const unhealthyRows = alertTimeline.filter((row) => isAlertingRow(row));
  const rows = onlyUnhealthy ? unhealthyRows : alertTimeline;
  const maxFailure = alertTimeline.length
    ? Math.max(...alertTimeline.map((row) => Number(row.failure ?? 0)))
    : 0;
  const maxRisk = alertTimeline.length
    ? Math.max(...alertTimeline.map((row) => Number(row.risk ?? 0)))
    : 0;

  return (
    <Card sx={{ height: 560 }}>
      <CardContent sx={{ height: "100%" }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mb: 1.2 }} alignItems={{ md: "center" }}>
          <Typography variant="h6">
          Alerts Explorer
          </Typography>
          <Chip label={`Total rows: ${alertTimeline.length}`} size="small" />
          <Chip label={`Alerting rows: ${unhealthyRows.length}`} size="small" color="warning" />
          <Chip label={`Max failure: ${Math.round(maxFailure)}`} size="small" />
          <Chip label={`Max risk: ${Math.round(maxRisk)}`} size="small" />
        </Stack>
        <FormControlLabel
          control={
            <Switch checked={onlyUnhealthy} onChange={(e) => setOnlyUnhealthy(e.target.checked)} />
          }
          label="Only alerting rows"
          sx={{ mb: 1 }}
        />
        {onlyUnhealthy && unhealthyRows.length === 0 && (
          <Alert severity="info" sx={{ mb: 1 }}>
            No active alert rows for current data slice. Turn off the filter to inspect the full timeline.
          </Alert>
        )}
        <div className="ag-theme-alpine-dark" style={{ height: 460, width: "100%" }}>
          <AgGridReact rowData={rows} columnDefs={colDefs} />
        </div>
      </CardContent>
    </Card>
  );
}

