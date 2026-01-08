import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { Alert, Box, Button, Grid, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";

import type { RCAReportResponse } from "../api/types";
import { createRcaReport } from "../api/endpoints";
import { defaultTimeWindow, buildWindowPayload, type TimeWindowState } from "../utils/timeWindow";
import { TimeWindowControls } from "../components/TimeWindowControls";
import { HealthDashboard } from "../components/HealthDashboard";

type LocationState = { report?: RCAReportResponse };

function str(v: unknown) {
  return v == null ? "" : String(v);
}

export function RcaPage() {
  const location = useLocation();
  const st = (location.state as LocationState | null)?.report;

  const [incidentId, setIncidentId] = useState<string>(str(st?.incident_id ?? ""));
  const [keyword, setKeyword] = useState<string>(str(st?.keyword ?? ""));
  const [window, setWindow] = useState<TimeWindowState>(() => defaultTimeWindow());
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createRcaReport,
    onError: (e: unknown) => {
      const maybe = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(maybe?.response?.data?.detail ?? maybe?.message ?? "Failed to generate report.");
    }
  });

  const report = (mutation.data ?? st) as RCAReportResponse | undefined;

  const executive = useMemo(() => {
    const ex = (report?.executive_summary ?? {}) as Record<string, unknown>;
    return {
      probable_change: str(ex.probable_change),
      recommended_fix: str(ex.recommended_fix),
      service_impacted: str(ex.service_impacted),
      title: str(ex.title),
      description: str(ex.description)
    };
  }, [report]);

  async function onGenerate() {
    setError(null);
    if (!keyword.trim() && !incidentId.trim()) {
      setError("Provide at least incident_id or keyword.");
      return;
    }
    const win = buildWindowPayload(window);
    mutation.mutate({
      incident_id: incidentId.trim() || null,
      keyword: keyword.trim() || null,
      lookback_hours: win.lookback_hours,
      start_utc: win.start_utc ?? null,
      end_utc: win.end_utc ?? null,
      include_aiops_combined: true
    });
  }

  const combined = ((report?.aiops ?? {}) as Record<string, unknown>).combined as
    | Record<string, unknown>
    | undefined;

  return (
    <Stack spacing={2}>
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          RCA Wizard / Detailed Incident Report
        </Typography>

        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Stack spacing={1.5}>
              <TextField
                label="incident_id (optional)"
                value={incidentId}
                onChange={(e) => setIncidentId(e.target.value)}
                fullWidth
              />
              <TextField
                label="keyword (optional if incident_id is provided)"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                fullWidth
              />
              <Button variant="contained" onClick={onGenerate} disabled={mutation.isPending}>
                {mutation.isPending ? "Generating…" : "Generate report"}
              </Button>
            </Stack>
          </Grid>
          <Grid item xs={12} md={6}>
            <TimeWindowControls value={window} onChange={setWindow} />
          </Grid>
        </Grid>
      </Paper>

      {report ? (
        <Paper sx={{ p: 2 }}>
          <Typography variant="overline" sx={{ opacity: 0.7 }}>
            Executive Summary — Most Probable Cause
          </Typography>
          <Box sx={{ mt: 1 }}>
            <Typography variant="subtitle1" sx={{ color: "secondary.main" }}>
              Most Probable Change
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {executive.probable_change || "N/A"}
            </Typography>
          </Box>
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1" sx={{ color: "secondary.main" }}>
              Recommended Fix
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              {executive.recommended_fix || "N/A"}
            </Typography>
          </Box>
        </Paper>
      ) : null}

      {combined ? <HealthDashboard data={combined} title="2.0 Combined cluster health deviation (Infra + App + Logs)" /> : null}

      {report && !combined ? (
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle1">AIOps data</Typography>
          <Typography variant="body2" sx={{ opacity: 0.7 }}>
            Report generated, but combined AIOps payload is missing (check backend `/summarize_combined`).
          </Typography>
        </Paper>
      ) : null}
    </Stack>
  );
}

