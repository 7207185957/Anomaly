"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import {
  AuthModeResponse,
  ClusterHealthResponse,
  CombinedSummaryResponse,
  IncidentSummaryResponse,
  JobStatusResponse,
  JobSubmitResponse,
  LogsResponse,
  LoginResponse,
  OpenIncidentsResponse,
  TimeWindowPayload,
  TopologyResponse,
} from "@/types/api";

export const useLogin = () =>
  useMutation({
    mutationFn: async (payload: { username: string; password: string }) => {
      const { data } = await api.post<LoginResponse>("/auth/login", payload);
      return data;
    },
  });

export const useCurrentUser = (enabled = true) =>
  useQuery({
    queryKey: ["auth", "me"],
    enabled,
    queryFn: async () => {
      const { data } = await api.get("/auth/me");
      return data as { username: string; display_name: string; groups: string[]; is_admin: boolean };
    },
    staleTime: 60_000,
  });

export const useAuthMode = () =>
  useQuery({
    queryKey: ["auth", "mode"],
    queryFn: async () => {
      const { data } = await api.get<AuthModeResponse>("/auth/mode");
      return data;
    },
    staleTime: 60_000,
  });

export const useCombinedSummary = (payload: TimeWindowPayload, enabled: boolean) =>
  useQuery({
    queryKey: ["summary", "combined", payload],
    enabled,
    queryFn: async () => {
      const { data } = await api.post<CombinedSummaryResponse>("/summaries/combined", payload);
      return data;
    },
    refetchInterval: 30_000,
  });

export const useOpenIncidents = (
  payload: {
    keyword?: string;
    lookback_hours?: number;
    start_utc?: string;
    end_utc?: string;
    team_name?: string;
    include_resolved?: boolean;
  },
  enabled: boolean,
) =>
  useQuery({
    queryKey: ["incidents", "open", payload],
    enabled,
    queryFn: async () => {
      const { data } = await api.post<OpenIncidentsResponse>("/incidents/open", payload);
      return data;
    },
    refetchInterval: 30_000,
  });

export const useIncidentSummary = () =>
  useMutation({
    mutationFn: async (payload: { incident: Record<string, unknown>; context?: Record<string, unknown> }) => {
      const { data } = await api.post<IncidentSummaryResponse>("/incidents/summarize", payload);
      return data;
    },
  });

export const useClusterHealth = (payload: TimeWindowPayload, enabled: boolean) =>
  useQuery({
    queryKey: ["cluster", "health", payload],
    enabled,
    queryFn: async () => {
      const { data } = await api.post<ClusterHealthResponse>("/cluster/health", payload);
      return data;
    },
    refetchInterval: 20_000,
  });

export const useTopology = (keyword: string, regionFilter: string[], enabled: boolean) =>
  useQuery({
    queryKey: ["topology", keyword, regionFilter],
    enabled,
    queryFn: async () => {
      const { data } = await api.post<TopologyResponse>("/topology/graph", {
        keyword,
        region_filter: regionFilter,
      });
      return data;
    },
  });

export const useLogs = (params: { logql: string; start_utc: string; end_utc: string; group_by_host_ip?: boolean }, enabled: boolean) =>
  useQuery({
    queryKey: ["logs", params],
    enabled,
    queryFn: async () => {
      const { data } = await api.post<LogsResponse>("/logs/query", params);
      return data;
    },
  });

export const useSubmitRcaJob = () =>
  useMutation({
    mutationFn: async (payload: { keyword: string; context: Record<string, unknown> }) => {
      const { data } = await api.post<JobSubmitResponse>("/jobs/rca", payload);
      return data;
    },
  });

export const useJobStatus = (jobId: string | null) =>
  useQuery({
    queryKey: ["jobs", jobId],
    enabled: Boolean(jobId),
    queryFn: async () => {
      const { data } = await api.get<JobStatusResponse>(`/jobs/${jobId}`);
      return data;
    },
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status && (status === "queued" || status === "started" || status === "deferred")
        ? 2000
        : false;
    },
  });

