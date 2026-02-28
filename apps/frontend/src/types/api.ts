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
  counts: Record<string, number | string>;
};

export type CombinedSummaryResponse = {
  keyword: string;
  cluster_health: number;
  infra_anomaly_count?: number;
  app_anomaly_count?: number;
  infra_only: {
    cluster_health: number;
    health_failure_timeline: Array<Record<string, unknown>>;
  };
  app_only: {
    cluster_health: number;
    health_failure_timeline: Array<Record<string, unknown>>;
  };
  health_failure_timeline: Array<Record<string, unknown>>;
  app_log_error_count: number;
  dag_log_error_count: number;
  severity_breakdown: Record<string, number>;
  rca: Array<Record<string, unknown>>;
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

