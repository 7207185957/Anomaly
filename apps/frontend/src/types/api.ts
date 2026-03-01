export type TimeWindowPayload = {
  keyword: string;
  lookback_hours?: number;
  start_utc?: string;
  end_utc?: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  username: string;
  display_name: string;
  groups: string[];
};

export type AuthModeResponse = {
  demo_mode: boolean;
  demo_username_hint?: string | null;
};

export type ClusterHealthResponse = {
  keyword: string;
  health_score: number;
  health_signature: {
    health_state?: string;
    health_p10?: number;
    health_last?: number;
    archetypes?: Record<string, string>;
  };
  health_failure_timeline: Array<{
    minute: string;
    health: number;
    failure: number;
    risk: number;
    infra_anomalies: number;
    app_anomalies: number;
    app_log_errors: number;
    dag_log_errors: number;
    health_archetype?: string;
    health_sequence?: string;
  }>;
  asset_health_timeline?: Array<Record<string, unknown>>;
  infra_only?: {
    cluster_health: number;
    health_failure_timeline: Array<Record<string, unknown>>;
    asset_health_timeline?: Array<Record<string, unknown>>;
  };
  app_only?: {
    cluster_health: number;
    health_failure_timeline: Array<Record<string, unknown>>;
    asset_health_timeline?: Array<Record<string, unknown>>;
  };
  counts: Record<string, number | string>;
  debug?: Record<string, unknown>;
};

export type CombinedSummaryResponse = {
  keyword: string;
  cluster_health: number;
  infra_anomaly_count?: number;
  app_anomaly_count?: number;
  health_signature?: {
    health_state?: string;
    health_p10?: number;
    health_last?: number;
    archetypes?: Record<string, string>;
  };
  incidents?: Array<Record<string, unknown>>;
  asset_health_timeline?: Array<Record<string, unknown>>;
  infra_only: {
    cluster_health: number;
    health_failure_timeline: Array<Record<string, unknown>>;
    asset_health_timeline?: Array<Record<string, unknown>>;
  };
  app_only: {
    cluster_health: number;
    health_failure_timeline: Array<Record<string, unknown>>;
    asset_health_timeline?: Array<Record<string, unknown>>;
  };
  health_failure_timeline: Array<Record<string, unknown>>;
  app_log_error_count: number;
  dag_log_error_count: number;
  severity_breakdown: Record<string, number>;
  rca: Array<Record<string, unknown>>;
};

export type OpenIncidentsResponse = {
  team_name?: string | null;
  keyword?: string | null;
  since_utc?: string | null;
  until_utc?: string | null;
  count: number;
  incidents: Array<{
    incident_id?: string;
    title?: string;
    description?: string;
    severity?: string;
    status?: string;
    service_impacted?: string;
    team_name?: string;
    start_time?: string;
    end_time?: string | null;
    [key: string]: unknown;
  }>;
  summary: {
    status_breakdown?: Record<string, number>;
    severity_breakdown?: Record<string, number>;
    open_count?: number;
  };
};

export type IncidentSummaryResponse = {
  incident_id?: string | null;
  title: string;
  executive_summary: string;
  incident_summary: string;
  probable_cause: string;
  recommended_fix: string;
  generated_by: string;
  generated_at_utc?: string;
};

export type LogsResponse = {
  rows: Array<Record<string, unknown>>;
  total: number;
};

export type TopologyResponse = {
  nodes: Array<{ id: string; label: string }>;
  edges: Array<{ id: string; source: string; target: string; type: string }>;
  stats: Record<string, number>;
};

export type JobSubmitResponse = {
  job_id: string;
  queue: string;
  status: string;
  submitted_at: string;
};

export type JobStatusResponse = {
  job_id: string;
  status: string;
  result?: Record<string, unknown>;
  error?: string;
};

