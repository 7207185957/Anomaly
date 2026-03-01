"use client";

import { useMemo } from "react";
import { Alert, Box, Card, CardContent, CircularProgress, Grid, Stack, Typography } from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";

import { useCombinedSummary, useOpenIncidents } from "@/hooks/useAIOpsApi";
import { TimeWindowPayload } from "@/types/api";

type Props = {
  payload: TimeWindowPayload;
  enabled: boolean;
};

function severityRank(severity: unknown): number {
  const v = String(severity || "").toLowerCase();
  if (v.includes("critical") || v === "sev1") return 4;
  if (v.includes("high") || v === "sev2") return 3;
  if (v.includes("medium") || v === "sev3") return 2;
  if (v.includes("low") || v === "sev4") return 1;
  return 0;
}

function minuteLabel(value: unknown): string {
  const raw = String(value || "");
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw || "n/a";
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)} UTC`;
}

export function IncidentsModule({ payload, enabled }: Props) {
  const incidentsQuery = useOpenIncidents(
    {
      include_resolved: false,
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
  const highlightRows = [...incidentRows]
    .sort((a, b) => {
      const sevCmp = severityRank(b.severity) - severityRank(a.severity);
      if (sevCmp !== 0) return sevCmp;
      return String(b.start_time || "").localeCompare(String(a.start_time || ""));
    })
    .slice(0, 6);
  const byStatus = incidentRows.reduce<Record<string, number>>((acc, row) => {
    const k = String(row.status || "unknown").toLowerCase();
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});
  const byService = incidentRows.reduce<Record<string, number>>((acc, row) => {
    const k = String(row.service_impacted || "unknown");
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});
  const topServices = Object.entries(byService)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

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
            <Alert severity="info" sx={{ mb: 1 }}>
              Incident data is intentionally independent of keyword and time-window filters.
            </Alert>
            <div className="ag-theme-alpine-dark" style={{ height: 370, width: "100%" }}>
              <AgGridReact rowData={incidentRows} columnDefs={incidentCols} />
            </div>
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Card sx={{ height: 300 }}>
          <CardContent sx={{ height: "100%" }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Incident Highlights
            </Typography>
            {highlightRows.length ? (
              <Stack spacing={0.75}>
                {highlightRows.map((row, idx) => (
                  <Typography key={`${row.incident_id || "incident"}-${idx}`} variant="body2">
                    <strong>#{idx + 1}</strong> [{String(row.severity || "unknown").toUpperCase()}]{" "}
                    {String(row.title || row.incident_id || "Incident")} | {String(row.service_impacted || "n/a")} |{" "}
                    {minuteLabel(row.start_time)}
                  </Typography>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" sx={{ opacity: 0.8 }}>
                No incident details available.
              </Typography>
            )}
          </CardContent>
        </Card>
      </Grid>
      <Grid size={{ xs: 12, lg: 6 }}>
        <Card sx={{ height: 300 }}>
          <CardContent sx={{ height: "100%" }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Incident Breakdown
            </Typography>
            <Box sx={{ mb: 1.25 }}>
              <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                By Status
              </Typography>
              <Stack spacing={0.45}>
                {Object.entries(byStatus).length ? (
                  Object.entries(byStatus).map(([k, v]) => (
                    <Typography key={k} variant="body2">
                      {k}: {v}
                    </Typography>
                  ))
                ) : (
                  <Typography variant="body2">No status data</Typography>
                )}
              </Stack>
            </Box>
            <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
              Top Services
            </Typography>
            <Stack spacing={0.45}>
              {topServices.length ? (
                topServices.map(([svc, count]) => (
                  <Typography key={svc} variant="body2">
                    {svc}: {count}
                  </Typography>
                ))
              ) : (
                <Typography variant="body2">No service data</Typography>
              )}
            </Stack>
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

