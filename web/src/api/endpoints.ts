import { api } from "./client";
import type {
  AIOpsSummaryRequest,
  AlertRow,
  Incident,
  KeywordsExtractResponse,
  RCAReportRequest,
  RCAReportResponse
} from "./types";

export async function fetchIncidents(params?: {
  limit?: number;
  offset?: number;
}): Promise<Incident[]> {
  const resp = await api.get("/incidents", { params });
  return (resp.data?.items ?? []) as Incident[];
}

export async function fetchAlerts(params?: {
  incident_id?: string;
  limit?: number;
  offset?: number;
}): Promise<AlertRow[]> {
  const resp = await api.get("/alerts", { params });
  return (resp.data?.items ?? []) as AlertRow[];
}

export async function extractKeywords(texts: string[]): Promise<KeywordsExtractResponse> {
  const resp = await api.post("/keywords/extract", { texts });
  return resp.data as KeywordsExtractResponse;
}

export async function aiopsCombined(req: AIOpsSummaryRequest): Promise<Record<string, unknown>> {
  const resp = await api.post("/aiops/summary_combined", req);
  return resp.data as Record<string, unknown>;
}

export async function aiopsInfra(req: AIOpsSummaryRequest): Promise<Record<string, unknown>> {
  const resp = await api.post("/aiops/summary", req);
  return resp.data as Record<string, unknown>;
}

export async function aiopsApp(req: AIOpsSummaryRequest): Promise<Record<string, unknown>> {
  const resp = await api.post("/aiops/summary_app", req);
  return resp.data as Record<string, unknown>;
}

export async function createRcaReport(req: RCAReportRequest): Promise<RCAReportResponse> {
  const resp = await api.post("/rca/report", req);
  return resp.data as RCAReportResponse;
}

