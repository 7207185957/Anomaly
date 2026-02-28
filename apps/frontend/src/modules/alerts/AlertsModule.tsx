"use client";

import { useMemo, useState } from "react";
import { Alert, Card, CardContent, CircularProgress, FormControlLabel, Switch, Typography } from "@mui/material";
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

export function AlertsModule({ payload, enabled }: Props) {
  const [onlyUnhealthy, setOnlyUnhealthy] = useState(true);
  const query = useClusterHealth(payload, enabled);

  const colDefs = useMemo<ColDef[]>(
    () => [
      { field: "minute", headerName: "Minute (UTC)", minWidth: 220, flex: 1 },
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
    return <Alert severity="info">Provide a keyword to load alerts.</Alert>;
  }
  if (query.isLoading) return <CircularProgress />;
  if (query.isError || !query.data) return <Alert severity="error">Failed to load alerts.</Alert>;

  const timeline = query.data.health_failure_timeline || [];
  const rows = onlyUnhealthy
    ? timeline.filter((row) => !healthyArchetypes.has(String(row.health_archetype || "").toUpperCase()))
    : timeline;

  return (
    <Card sx={{ height: 560 }}>
      <CardContent sx={{ height: "100%" }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Alerts Explorer
        </Typography>
        <FormControlLabel
          control={
            <Switch checked={onlyUnhealthy} onChange={(e) => setOnlyUnhealthy(e.target.checked)} />
          }
          label="Only unhealthy archetypes"
          sx={{ mb: 1 }}
        />
        <div className="ag-theme-alpine-dark" style={{ height: 460, width: "100%" }}>
          <AgGridReact rowData={rows} columnDefs={colDefs} />
        </div>
      </CardContent>
    </Card>
  );
}

