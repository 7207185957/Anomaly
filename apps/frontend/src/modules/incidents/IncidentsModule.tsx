"use client";

import { useMemo } from "react";
import { Alert, Card, CardContent, CircularProgress, Grid, Typography } from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";

import { useCombinedSummary, useOpenIncidents } from "@/hooks/useAIOpsApi";
import { TimeWindowPayload } from "@/types/api";

type Props = {
  payload: TimeWindowPayload;
  enabled: boolean;
};

export function IncidentsModule({ payload, enabled }: Props) {
  const incidentsQuery = useOpenIncidents(
    {
      include_resolved: false,
      keyword: payload.keyword || undefined,
      lookback_hours: payload.lookback_hours,
      start_utc: payload.start_utc,
      end_utc: payload.end_utc,
    },
    enabled,
  );
  const query = useCombinedSummary(payload, enabled && Boolean(payload.keyword));

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

  const incidentCols = useMemo<ColDef[]>(
    () => [
      { field: "incident_id", headerName: "Incident", minWidth: 140 },
      { field: "title", headerName: "Title", minWidth: 260, flex: 2 },
      { field: "severity", headerName: "Severity", width: 110 },
      { field: "status", headerName: "Status", width: 120 },
      { field: "service_impacted", headerName: "Service", minWidth: 180, flex: 1 },
      { field: "team_name", headerName: "Team", minWidth: 160 },
      { field: "start_time", headerName: "Start Time", minWidth: 220, flex: 1 },
      { field: "description", headerName: "Description", minWidth: 320, flex: 2 },
    ],
    [],
  );

  if (!enabled) {
    return <Alert severity="info">Incidents are disabled until authentication is complete.</Alert>;
  }
  if (incidentsQuery.isLoading) {
    return <CircularProgress />;
  }
  if (incidentsQuery.isError || !incidentsQuery.data) {
    return <Alert severity="error">Failed to load incident module.</Alert>;
  }

  const incidentData = incidentsQuery.data;
  const data = query.data;
  const rcaRows = Array.isArray(data?.rca) ? data?.rca : [];
  const incidentRows = Array.isArray(incidentData.incidents) ? incidentData.incidents : [];

  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Open Incidents</Typography>
            <Typography variant="h4">{incidentData.summary?.open_count ?? incidentData.count ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Incident Rows</Typography>
            <Typography variant="h4">{incidentData.count ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">High Severity</Typography>
            <Typography variant="h4">{incidentData.summary?.severity_breakdown?.high ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, md: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="overline">Medium Severity</Typography>
            <Typography variant="h4">{incidentData.summary?.severity_breakdown?.medium ?? 0}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card sx={{ height: 450 }}>
          <CardContent sx={{ height: "100%" }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Live Incidents (Backend-sourced)
            </Typography>
            <div className="ag-theme-alpine-dark" style={{ height: 370, width: "100%" }}>
              <AgGridReact rowData={incidentRows} columnDefs={incidentCols} />
            </div>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={12}>
        <Card sx={{ height: 430 }}>
          <CardContent sx={{ height: "100%" }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              RCA Recommendations
            </Typography>
            {payload.keyword ? (
              <div className="ag-theme-alpine-dark" style={{ height: 350, width: "100%" }}>
                <AgGridReact rowData={rcaRows} columnDefs={colDefs} />
              </div>
            ) : (
              <Alert severity="info">Enter a keyword in global filters to generate anomaly RCA recommendations.</Alert>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

