import Plot from "react-plotly.js";
import { Box, Grid, Paper, Stack, Typography } from "@mui/material";

type AnyRecord = Record<string, unknown>;
type HoverRow = [number, number, number, number, number];
type PlotTrace = {
  x: string[];
  y: number[];
  type: "scatter";
  mode: "lines";
  name: string;
  line: { color: string; width: number };
  customdata?: HoverRow[];
  hovertemplate?: string;
};

function num(v: unknown, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export function HealthDashboard(props: { data: AnyRecord; title?: string }) {
  const title = props.title ?? "Combined cluster health deviation";
  const hf = (props.data?.health_failure_timeline as AnyRecord[] | undefined) ?? [];
  const sig = (props.data?.health_signature as AnyRecord | undefined) ?? {};

  if (!hf.length) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1">{title}</Typography>
        <Typography variant="body2" sx={{ opacity: 0.7 }}>
          No health_failure_timeline data returned.
        </Typography>
      </Paper>
    );
  }

  const x = hf.map((r) => String(r.minute ?? ""));
  const health = hf.map((r) => num(r.health));
  const failure = hf.map((r) => num(r.failure));
  const risk = hf.map((r) => num(r.risk));

  const last = hf[hf.length - 1] ?? {};
  const infra = num(last.infra_anomalies);
  const app = num(last.app_anomalies);
  const appLogs = num(last.app_log_errors);
  const dagLogs = num(last.dag_log_errors);
  const total = num(last.total_events, infra + app + appLogs + dagLogs);

  const healthState = String(sig.health_state ?? "N/A");
  const failureState = String(sig.failure_state ?? "N/A");
  const riskState = String(sig.risk_state ?? "N/A");
  const signatureId = String(sig.signature_id ?? "H?");
  const confidence = num(sig.confidence, 0);

  const custom: HoverRow[] = hf.map((r) => [
    num(r.infra_anomalies),
    num(r.app_anomalies),
    num(r.total_anomalies ?? r.total_events),
    num(r.app_log_errors),
    num(r.dag_log_errors)
  ]);

  const traces: PlotTrace[] = [
    {
      x,
      y: health,
      type: "scatter",
      mode: "lines",
      name: "Health",
      line: { color: "#2ECC71", width: 2 },
      customdata: custom,
      hovertemplate:
        "time=%{x}<br>Health=%{y:.1f}<br>" +
        "Infra anomalies=%{customdata[0]}<br>" +
        "App anomalies=%{customdata[1]}<br>" +
        "Total anomalies=%{customdata[2]}<br>" +
        "App log errors=%{customdata[3]}<br>" +
        "DAG log errors=%{customdata[4]}<extra></extra>"
    },
    {
      x,
      y: failure,
      type: "scatter",
      mode: "lines",
      name: "Failure",
      line: { color: "#E74C3C", width: 2 },
      customdata: custom,
      hovertemplate:
        "time=%{x}<br>Failure=%{y:.1f}<br>" +
        "Infra anomalies=%{customdata[0]}<br>" +
        "App anomalies=%{customdata[1]}<br>" +
        "Total anomalies=%{customdata[2]}<br>" +
        "App log errors=%{customdata[3]}<br>" +
        "DAG log errors=%{customdata[4]}<extra></extra>"
    },
    {
      x,
      y: risk,
      type: "scatter",
      mode: "lines",
      name: "Risk",
      line: { color: "#F39C12", width: 2 }
    }
  ];

  return (
    <Stack spacing={2}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="overline" sx={{ opacity: 0.7 }}>
              Health State
            </Typography>
            <Typography variant="h6">{healthState}</Typography>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Failure: {failureState}
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Risk: {riskState}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="overline" sx={{ opacity: 0.7 }}>
              Signature
            </Typography>
            <Typography variant="h6">{signatureId}</Typography>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Confidence: {confidence}%
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="overline" sx={{ opacity: 0.7 }}>
              Latest totals (last point)
            </Typography>
            <Typography variant="body2">Infra anomalies: {infra}</Typography>
            <Typography variant="body2">App anomalies: {app}</Typography>
            <Typography variant="body2">App log errors: {appLogs}</Typography>
            <Typography variant="body2">DAG log errors: {dagLogs}</Typography>
            <Typography variant="body2">Total: {total}</Typography>
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: 1.5 }}>
        <Typography variant="subtitle1" sx={{ px: 1, pb: 1 }}>
          {title}
        </Typography>
        <Box sx={{ height: 520 }}>
          <Plot
            data={traces}
            layout={{
              autosize: true,
              height: 500,
              margin: { l: 50, r: 20, t: 10, b: 45 },
              legend: { orientation: "h" },
              xaxis: { title: { text: "Time (UTC)" }, type: "date" },
              yaxis: { title: { text: "Score (0–100)" }, range: [0, 100] },
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)"
            }}
            config={{ displaylogo: false, responsive: true }}
            style={{ width: "100%", height: "100%" }}
          />
        </Box>
      </Paper>
    </Stack>
  );
}

