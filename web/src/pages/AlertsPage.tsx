import { useState } from "react";
import { Alert, Box, Paper, Stack, TextField, Typography } from "@mui/material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useQuery } from "@tanstack/react-query";

import { fetchAlerts } from "../api/endpoints";
import type { AlertRow } from "../api/types";

function str(v: unknown) {
  return v == null ? "" : String(v);
}

export function AlertsPage() {
  const [incidentId, setIncidentId] = useState<string>("");

  const q = useQuery({
    queryKey: ["alerts-page", incidentId],
    queryFn: () => fetchAlerts({ incident_id: incidentId || undefined, limit: 5000, offset: 0 })
  });

  const rows = ((q.data ?? []) as AlertRow[]).map((a, idx) => ({ id: str(a.alert_id || idx), ...a }));

  const cols: GridColDef[] = [
    { field: "alert_time", headerName: "Alert time", width: 190 },
    { field: "alert_id", headerName: "Alert ID", width: 170 },
    { field: "incident_id", headerName: "Incident ID", width: 170 },
    { field: "service", headerName: "Service", width: 220 },
    { field: "severity", headerName: "Severity", width: 120 },
    { field: "alert_name", headerName: "Alert name", flex: 1, minWidth: 260 }
  ];

  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Alerts
        </Typography>
        <TextField
          label="Filter by incident_id (optional)"
          value={incidentId}
          onChange={(e) => setIncidentId(e.target.value)}
          fullWidth
        />
      </Paper>

      {q.isError ? <Alert severity="error">Failed to load alerts.</Alert> : null}

      <Paper sx={{ p: 2 }}>
        <Box sx={{ height: 720 }}>
          <DataGrid
            rows={rows}
            columns={cols}
            loading={q.isLoading}
            disableRowSelectionOnClick
            pageSizeOptions={[25, 50, 100]}
            initialState={{ pagination: { paginationModel: { pageSize: 50, page: 0 } } }}
            sx={{ border: "none" }}
          />
        </Box>
      </Paper>
    </Stack>
  );
}

