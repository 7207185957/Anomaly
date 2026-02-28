"use client";

import { useMemo, useState } from "react";
import { Alert, Button, Card, CardContent, CircularProgress, Stack, TextField, Typography } from "@mui/material";

import { useJobStatus, useSubmitRcaJob } from "@/hooks/useAIOpsApi";

type Props = {
  keyword: string;
  enabled: boolean;
};

export function RcaJobsModule({ keyword, enabled }: Props) {
  const [contextInput, setContextInput] = useState("{}");
  const submit = useSubmitRcaJob();
  const statusQuery = useJobStatus(submit.data?.job_id || null);

  const parsedContext = useMemo(() => {
    try {
      return JSON.parse(contextInput);
    } catch {
      return null;
    }
  }, [contextInput]);

  if (!enabled) return <Alert severity="info">Provide a keyword first.</Alert>;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          RCA Async Jobs
        </Typography>
        <Stack spacing={2}>
          <TextField
            label="Context JSON"
            value={contextInput}
            onChange={(e) => setContextInput(e.target.value)}
            multiline
            minRows={5}
            error={parsedContext === null}
            helperText={parsedContext === null ? "Invalid JSON" : "This context is sent to the job worker."}
          />
          <Button
            variant="contained"
            disabled={parsedContext === null || submit.isPending}
            onClick={() => submit.mutate({ keyword, context: parsedContext || {} })}
          >
            Submit RCA Job
          </Button>
          {submit.isPending && <CircularProgress />}
          {submit.isError && <Alert severity="error">Failed to submit job.</Alert>}
          {submit.data && (
            <Alert severity="success">
              Job submitted: <strong>{submit.data.job_id}</strong>
            </Alert>
          )}
          {statusQuery.data && (
            <Card variant="outlined">
              <CardContent>
                <Typography>Status: {statusQuery.data.status}</Typography>
                {statusQuery.data.result && (
                  <pre style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
                    {JSON.stringify(statusQuery.data.result, null, 2)}
                  </pre>
                )}
                {statusQuery.data.error && (
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {statusQuery.data.error}
                  </Alert>
                )}
              </CardContent>
            </Card>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

