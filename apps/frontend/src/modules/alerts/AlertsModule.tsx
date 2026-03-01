"use client";

import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
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

const minuteLabel = (minuteValue: unknown) => {
  const raw = String(minuteValue || "");
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw || "n/a";
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)} UTC`;
};

const bucketUtcLabel = (minuteValue: unknown) => {
  const raw = String(minuteValue || "");
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw || "n/a";
  return d.toISOString().replace("Z", "+00:00");
};

const xTimeLabel = (minuteValue: unknown) => {
  const raw = String(minuteValue || "");
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw || "n/a";
  return d.toISOString().slice(0, 19).replace("T", " ");
};

export function AlertsModule({ payload, enabled }: Props) {
  const [onlyUnhealthy, setOnlyUnhealthy] = useState(false);
  const [selectedBuckets, setSelectedBuckets] = useState<string[]>([]);
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
  const archetypeRows = alertTimeline.map((row) => ({
    bucket_utc: bucketUtcLabel(row.minute),
    x_time: xTimeLabel(row.minute),
    health_archetype: row.health_archetype || "UNKNOWN",
    health_sequence: row.health_sequence || "N/A",
  }));
  const topAlertRows = [...unhealthyRows]
    .sort((a, b) => {
      const aScore =
        Number(a.failure ?? 0) * 1.2 +
        Number(a.risk ?? 0) * 1.1 +
        Number(a.infra_anomalies ?? 0) * 4 +
        Number(a.app_anomalies ?? 0) * 4 +
        Number(a.app_log_errors ?? 0) * 0.8 +
        Number(a.dag_log_errors ?? 0) * 0.8;
      const bScore =
        Number(b.failure ?? 0) * 1.2 +
        Number(b.risk ?? 0) * 1.1 +
        Number(b.infra_anomalies ?? 0) * 4 +
        Number(b.app_anomalies ?? 0) * 4 +
        Number(b.app_log_errors ?? 0) * 0.8 +
        Number(b.dag_log_errors ?? 0) * 0.8;
      return bScore - aScore;
    })
    .slice(0, 6);
  const toggleBucket = (bucketUtc: string) => {
    setSelectedBuckets((prev) =>
      prev.includes(bucketUtc) ? prev.filter((x) => x !== bucketUtc) : [...prev, bucketUtc],
    );
  };
  const debugInfo = query.data.debug || {};

  return (
    <Stack spacing={2}>
      <Card sx={{ height: 720 }}>
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
          <Box
            sx={{
              mb: 1.2,
              p: 1.1,
              borderRadius: 1.5,
              border: "1px solid rgba(148,163,184,0.22)",
              background: "linear-gradient(135deg, rgba(11,18,32,0.75) 0%, rgba(17,24,39,0.82) 100%)",
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 0.6 }}>
              Active Alert Insights
            </Typography>
            {topAlertRows.length ? (
              <Stack spacing={0.55}>
                {topAlertRows.map((row, idx) => (
                  <Typography key={`${row.minute}-${idx}`} variant="body2">
                    <strong>#{idx + 1}</strong> {minuteLabel(row.minute)} |{" "}
                    {String(row.alert_reason || "informational")} | health={Number(row.health ?? 0).toFixed(1)} |{" "}
                    failure={Number(row.failure ?? 0).toFixed(1)} | risk={Number(row.risk ?? 0).toFixed(1)} | infra=
                    {Number(row.infra_anomalies ?? 0)} | app={Number(row.app_anomalies ?? 0)}
                  </Typography>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" sx={{ opacity: 0.82 }}>
                No active alerts in this slice.
              </Typography>
            )}
          </Box>
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
          <div className="ag-theme-alpine-dark" style={{ height: 470, width: "100%" }}>
            <AgGridReact rowData={rows} columnDefs={colDefs} />
          </div>
        </CardContent>
      </Card>

      <Card sx={{ height: 470 }}>
        <CardContent sx={{ height: "100%" }}>
          <Typography variant="h5" sx={{ mb: 1.2 }}>
            Archetypes + sequences over time
          </Typography>
          <Alert severity="info" sx={{ mb: 1.2 }}>
            Logic (same as Streamlit): health sequence is derived from rolling 15-minute health symbols (A-E), and
            health archetype is classified from sequence pattern transitions (stable, degrading, recovered, flapping).
          </Alert>
          {archetypeRows.length ? (
            <TableContainer
              component={Paper}
              sx={{
                maxHeight: 330,
                background: "transparent",
                border: "1px solid rgba(148,163,184,0.25)",
              }}
            >
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>bucket_utc</TableCell>
                    <TableCell>x_time</TableCell>
                    <TableCell>health_archetype</TableCell>
                    <TableCell>health_sequence</TableCell>
                    <TableCell width={90}>Select</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {archetypeRows.map((row) => (
                    <TableRow key={row.bucket_utc} hover selected={selectedBuckets.includes(row.bucket_utc)}>
                      <TableCell>{row.bucket_utc}</TableCell>
                      <TableCell>{row.x_time}</TableCell>
                      <TableCell>{row.health_archetype}</TableCell>
                      <TableCell>{row.health_sequence}</TableCell>
                      <TableCell>
                        <Checkbox
                          checked={selectedBuckets.includes(row.bucket_utc)}
                          onChange={() => toggleBucket(row.bucket_utc)}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="warning">
              No archetype rows were returned by cluster health timeline. Debug: combined_anomaly_count=
              {String(debugInfo.combined_anomaly_count ?? "n/a")}, app_log_total=
              {String(debugInfo.app_log_total ?? "n/a")}, dag_log_total=
              {String(debugInfo.dag_log_total ?? "n/a")}.
            </Alert>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}

