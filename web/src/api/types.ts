export type Incident = Record<string, unknown> & {
  incident_id?: string;
  start_time?: string;
  end_time?: string;
  title?: string;
  description?: string;
  severity?: string;
  status?: string;
  service_impacted?: string;
  root_cause?: string;
};

export type AlertRow = Record<string, unknown> & {
  alert_id?: string;
  alert_time?: string;
  incident_id?: string;
  alert_name?: string;
  service?: string;
  severity?: string;
  resolved_time?: string;
};

export type KeywordsExtractResponse = {
  raw: string;
  keywords: string[];
};

export type AIOpsSummaryRequest = {
  keyword: string;
  lookback_hours: number;
  start_utc?: string | null;
  end_utc?: string | null;
};

export type RCAReportRequest = {
  incident_id?: string | null;
  keyword?: string | null;
  service_impacted?: string | null;
  title?: string | null;
  description?: string | null;
  lookback_hours: number;
  start_utc?: string | null;
  end_utc?: string | null;
  include_aiops_combined?: boolean;
  include_aiops_infra?: boolean;
  include_aiops_app?: boolean;
};

export type RCAReportResponse = {
  keyword: string;
  incident_id?: string | null;
  executive_summary: Record<string, unknown>;
  aiops: Record<string, unknown>;
};

