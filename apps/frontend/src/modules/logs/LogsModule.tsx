"use client";

import { useMemo, useState } from "react";
import { Alert, Button, Card, CardContent, CircularProgress, FormControlLabel, Switch, TextField, Typography } from "@mui/material";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";

import { useLogs } from "@/hooks/useAIOpsApi";
import { TimeWindowPayload } from "@/types/api";

type Props = {
  payload: TimeWindowPayload;
  enabled: boolean;
};

dayjs.extend(utc);

export function LogsModule({ payload, enabled }: Props) {
  const [logql, setLogql] = useState(
    '{job="promtail", service=~"rabbitmq-log|airflow-scheduler-log"} |= "error"',
  );
  const [groupByHost, setGroupByHost] = useState(false);
  const [run, setRun] = useState(false);

  const startUtc = payload.start_utc || dayjs().utc().subtract(payload.lookback_hours ?? 3, "hour").toISOString();
  const endUtc = payload.end_utc || dayjs().utc().toISOString();

  const params = useMemo(
    () => ({
      logql,
      start_utc: startUtc,
      end_utc: endUtc,
      group_by_host_ip: groupByHost,
    }),
    [logql, startUtc, endUtc, groupByHost],
  );

  const query = useLogs(params, enabled && run);

  const colDefs = useMemo<ColDef[]>(
    () => [
      { field: "timestamp", headerName: "Timestamp", minWidth: 220, flex: 1 },
      { field: "host_ip", headerName: "Host IP", width: 140 },
      { field: "service", headerName: "Service", minWidth: 180, flex: 1 },
      { field: "filename", headerName: "File", minWidth: 260, flex: 2 },
      { field: "log", headerName: "Log", minWidth: 500, flex: 4 },
    ],
    [],
  );

  if (!enabled) return <Alert severity="info">Provide a keyword first.</Alert>;

  return (
    <Card sx={{ height: 620 }}>
      <CardContent sx={{ height: "100%" }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Logs Insight
        </Typography>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 220px 180px", gap: 12 }}>
          <TextField
            label="LogQL"
            value={logql}
            onChange={(e) => setLogql(e.target.value)}
            fullWidth
          />
          <FormControlLabel
            label="Group by host"
            control={
              <Switch checked={groupByHost} onChange={(e) => setGroupByHost(e.target.checked)} />
            }
          />
          <Button variant="contained" onClick={() => setRun(true)}>
            Run Query
          </Button>
        </div>
        {!run && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Press &quot;Run Query&quot; to load logs for selected time window.
          </Alert>
        )}
        {query.isLoading && <CircularProgress sx={{ mt: 2 }} />}
        {query.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            Failed to query logs.
          </Alert>
        )}
        {query.data && !query.isLoading && (
          <>
            <Typography sx={{ mt: 2, mb: 1 }}>
              Rows returned: {query.data.total}
            </Typography>
            <div className="ag-theme-alpine-dark" style={{ height: 470, width: "100%" }}>
              <AgGridReact rowData={query.data.rows as Record<string, unknown>[]} columnDefs={colDefs} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

