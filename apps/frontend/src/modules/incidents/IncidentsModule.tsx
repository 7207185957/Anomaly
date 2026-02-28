"use client";

import { useMemo } from "react";
import { Alert, Card, CardContent, CircularProgress, Grid, Typography } from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";

import { useCombinedSummary } from "@/hooks/useAIOpsApi";
import { TimeWindowPayload } from "@/types/api";

type Props = {
  payload: TimeWindowPayload;
  enabled: boolean;
};

export function IncidentsModule({ payload, enabled }: Props) {
  const query = useCombinedSummary(payload, enabled);

  const colDefs = useMemo<ColDef[]>(
    () => [
      { field: "metric", headerName: "Metric", flex: 1 },
      { field: "asset_id", headerName: "Asset", flex: 1 },
      { field: "anomaly_count", headerName: "Anomaly Count", width: 140 },
      { field: "summary", headerName: "Summary", flex: 2 },
      { field: "recommendation", headerName: "Recommendation", flex: 2 },
    ],
    [],
  );

  if (!enabled) {
    return <Alert severity="info">Provide a keyword to load incident insights.</Alert>;
  }
  if (query.isLoading) {
    return <CircularProgress />;
  }
  if (query.isError || !query.data) {
    return <Alert severity="error">Failed to load incident module.</Alert>;
  }

  const data = query.data;
  const rcaRows = Array.isArray(data.rca) ? data.rca : [];

  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Cluster Health</Typography>
            <Typography variant="h4">{data.cluster_health}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Infra Anomalies</Typography>
            <Typography variant="h4">{data.infra_anomaly_count ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">App Anomalies</Typography>
            <Typography variant="h4">{data.app_anomaly_count ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">DAG Error Logs</Typography>
            <Typography variant="h4">{data.dag_log_error_count ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card sx={{ height: 430 }}>
          <CardContent sx={{ height: "100%" }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              RCA Recommendations
            </Typography>
            <div className="ag-theme-alpine-dark" style={{ height: 350, width: "100%" }}>
              <AgGridReact rowData={rcaRows} columnDefs={colDefs} />
            </div>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

