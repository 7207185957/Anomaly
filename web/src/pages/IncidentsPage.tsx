import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Grid,
  Paper,
  Stack,
  Typography
} from "@mui/material";
import { DataGrid, GridColDef, GridRowSelectionModel } from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";

import { extractKeywords, fetchAlerts, fetchIncidents } from "../api/endpoints";
import type { AlertRow, Incident } from "../api/types";
import { defaultTimeWindow, buildWindowPayload, type TimeWindowState } from "../utils/timeWindow";
import { TimeWindowControls } from "../components/TimeWindowControls";
import { createRcaReport } from "../api/endpoints";
import { useNavigate } from "react-router-dom";

function str(v: unknown) {
  return v == null ? "" : String(v);
}

export function IncidentsPage() {
  const nav = useNavigate();

  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([
    "title",
    "description",
    "service_impacted",
    "severity"
  ]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  const [window, setWindow] = useState<TimeWindowState>(() => defaultTimeWindow());
  const [error, setError] = useState<string | null>(null);

  const incidentsQ = useQuery({
    queryKey: ["incidents"],
    queryFn: () => fetchIncidents({ limit: 500, offset: 0 })
  });

  const incidents = incidentsQ.data ?? [];

  const selectedIncident: Incident | undefined = useMemo(() => {
    if (!selectedIncidentId) return undefined;
    return incidents.find((i) => str(i.incident_id) === selectedIncidentId);
  }, [incidents, selectedIncidentId]);

  const alertsQ = useQuery({
    queryKey: ["alerts", selectedIncidentId],
    queryFn: () => fetchAlerts({ incident_id: selectedIncidentId ?? undefined, limit: 5000, offset: 0 }),
    enabled: Boolean(selectedIncidentId)
  });
  const alerts = (alertsQ.data ?? []) as AlertRow[];

  const incidentCols: GridColDef[] = [
    { field: "incident_id", headerName: "Incident ID", width: 170 },
    { field: "start_time", headerName: "Start", width: 190 },
    { field: "severity", headerName: "Severity", width: 120 },
    { field: "status", headerName: "Status", width: 120 },
    { field: "service_impacted", headerName: "Service", width: 220 },
    { field: "title", headerName: "Title", flex: 1, minWidth: 260 }
  ];

  const alertCols: GridColDef[] = [
    { field: "alert_time", headerName: "Alert time", width: 190 },
    { field: "alert_id", headerName: "Alert ID", width: 170 },
    { field: "service", headerName: "Service", width: 220 },
    { field: "severity", headerName: "Severity", width: 120 },
    { field: "alert_name", headerName: "Alert name", flex: 1, minWidth: 260 }
  ];

  const incidentRows = incidents.map((i, idx) => ({ id: str(i.incident_id || idx), ...i }));
  const alertRows = alerts.map((a, idx) => ({ id: str(a.alert_id || idx), ...a }));

  async function onExtractKeywords() {
    setError(null);
    if (!selectedIncident) {
      setError("Select exactly one incident first.");
      return;
    }

    // Build text list similarly to Streamlit: selected columns from incident + alerts
    const texts: string[] = [];
    for (const col of selectedColumns) {
      texts.push(str((selectedIncident as Record<string, unknown>)[col]));
      for (const a of alerts) {
        texts.push(str((a as Record<string, unknown>)[col]));
      }
    }

    try {
      const res = await extractKeywords(texts.filter(Boolean));
      const kws = res.keywords ?? [];
      setKeywords(kws);
      setSelectedKeyword(kws[0] ?? null);
    } catch (e: unknown) {
      const maybe = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(maybe?.response?.data?.detail ?? maybe?.message ?? "Keyword extraction failed.");
    }
  }

  async function onGenerateReport() {
    setError(null);
    const keyword = selectedKeyword?.trim();
    if (!selectedIncidentId) {
      setError("Select an incident first.");
      return;
    }
    if (!keyword) {
      setError("Select a keyword first (extract keywords, then choose one).");
      return;
    }

    const win = buildWindowPayload(window);

    try {
      const report = await createRcaReport({
        incident_id: selectedIncidentId,
        keyword,
        lookback_hours: win.lookback_hours,
        start_utc: win.start_utc ?? null,
        end_utc: win.end_utc ?? null,
        include_aiops_combined: true
      });

      nav("/rca", { state: { report } });
    } catch (e: unknown) {
      const maybe = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(maybe?.response?.data?.detail ?? maybe?.message ?? "RCA report generation failed.");
    }
  }

  const selectableColumns = useMemo(() => {
    const incidentKeys = selectedIncident ? Object.keys(selectedIncident) : [];
    const alertKeys = alerts[0] ? Object.keys(alerts[0] as Record<string, unknown>) : [];
    return Array.from(new Set([...incidentKeys, ...alertKeys])).sort();
  }, [selectedIncident, alerts]);

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={7}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Incidents
          </Typography>

          {incidentsQ.isError ? (
            <Alert severity="error">Failed to load incidents.</Alert>
          ) : null}

          <Box sx={{ height: 540 }}>
            <DataGrid
              rows={incidentRows}
              columns={incidentCols}
              loading={incidentsQ.isLoading}
              disableRowSelectionOnClick={false}
              rowSelectionModel={selectedIncidentId ? [selectedIncidentId] : []}
              onRowSelectionModelChange={(m: GridRowSelectionModel) => {
                const id = m?.[0] ? String(m[0]) : null;
                setSelectedIncidentId(id);
                setKeywords([]);
                setSelectedKeyword(null);
              }}
              pageSizeOptions={[25, 50, 100]}
              initialState={{
                pagination: { paginationModel: { pageSize: 25, page: 0 } }
              }}
              sx={{
                border: "none",
                "& .MuiDataGrid-row.Mui-selected": {
                  outline: "1px solid rgba(59,130,246,0.65)"
                }
              }}
            />
          </Box>
        </Paper>

        <Paper sx={{ p: 2, mt: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Alerts {selectedIncidentId ? <Chip size="small" label={`incident_id=${selectedIncidentId}`} /> : null}
          </Typography>
          <Box sx={{ height: 360 }}>
            <DataGrid
              rows={alertRows}
              columns={alertCols}
              loading={alertsQ.isLoading}
              disableRowSelectionOnClick
              pageSizeOptions={[25, 50, 100]}
              initialState={{
                pagination: { paginationModel: { pageSize: 25, page: 0 } }
              }}
              sx={{ border: "none" }}
            />
          </Box>
        </Paper>
      </Grid>

      <Grid item xs={12} md={5}>
        <Stack spacing={2}>
          {error ? <Alert severity="error">{error}</Alert> : null}

          <Paper sx={{ p: 2 }}>
            <TimeWindowControls value={window} onChange={setWindow} />
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Keyword extraction
            </Typography>
            <Stack spacing={1}>
              <Typography variant="body2" sx={{ opacity: 0.75 }}>
                Choose which fields to include (incident + alerts), then extract keywords using Ollama.
              </Typography>

              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                {selectableColumns.slice(0, 14).map((c) => {
                  const selected = selectedColumns.includes(c);
                  return (
                    <Chip
                      key={c}
                      label={c}
                      size="small"
                      color={selected ? "primary" : "default"}
                      variant={selected ? "filled" : "outlined"}
                      onClick={() => {
                        setSelectedColumns((prev) =>
                          prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
                        );
                      }}
                    />
                  );
                })}
              </Box>

              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  onClick={onExtractKeywords}
                  disabled={!selectedIncidentId || incidentsQ.isLoading}
                >
                  Extract keywords
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => {
                    setKeywords([]);
                    setSelectedKeyword(null);
                  }}
                >
                  Clear
                </Button>
              </Stack>

              {keywords.length ? (
                <Box>
                  <Typography variant="subtitle2" sx={{ mt: 1, mb: 1 }}>
                    Keywords
                  </Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                    {keywords.map((k) => (
                      <Chip
                        key={k}
                        label={k}
                        color={selectedKeyword === k ? "secondary" : "default"}
                        variant={selectedKeyword === k ? "filled" : "outlined"}
                        onClick={() => setSelectedKeyword(k)}
                      />
                    ))}
                  </Box>
                </Box>
              ) : null}
            </Stack>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              RCA Wizard
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.75, mb: 2 }}>
              Generates an executive summary + combined AIOps health data, then opens the report view.
            </Typography>
            <Button variant="contained" fullWidth onClick={onGenerateReport} disabled={!selectedIncidentId}>
              Generate RCA report
            </Button>
          </Paper>
        </Stack>
      </Grid>
    </Grid>
  );
}

