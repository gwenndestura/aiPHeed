// src/lib/queries.ts
// -------------------
// Typed TanStack Query hooks, one per backend endpoint. Components read data
// through these, never through api.ts directly -- that keeps caching,
// staleTime and query-key shape consistent across the app.
//
// staleTime ~1h on the quarter-stable reads (config, quarters, provinces,
// forecasts, explainability): the backend recomputes these per-quarter, not
// per-request, so refetching every render buys nothing. Admin reads use the
// query-library default (staleTime 0) since review/feedback state changes as
// a direct result of user actions in the same session.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  AuditResponse,
  ConfigResponse,
  ExplainabilityResponse,
  FeedbackCreated,
  FeedbackListResponse,
  FeedbackSubmitBody,
  ForecastResponse,
  Horizon,
  MunicipalitiesResponse,
  NewsResponse,
  ProvincesResponse,
  QuartersResponse,
  RejectionsResponse,
  ReviewItem,
  ReviewListResponse,
  Scope,
  SearchResponse,
  TimeseriesResponse,
} from "./apiTypes";

const HOUR = 60 * 60 * 1000;

// ---------------------------------------------------------------------------
// Public reads
// ---------------------------------------------------------------------------

export function useConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: () => api.get<ConfigResponse>("/api/v1/config", undefined, { auth: false }),
    staleTime: HOUR,
  });
}

export function useQuarters(horizon: Horizon = "nowcast") {
  return useQuery({
    queryKey: ["quarters", horizon],
    queryFn: () => api.get<QuartersResponse>("/api/v1/quarters", { horizon }, { auth: false }),
    staleTime: HOUR,
  });
}

export function useProvinces(quarter?: string, horizon: Horizon = "nowcast") {
  return useQuery({
    queryKey: ["provinces", quarter, horizon],
    queryFn: () => api.get<ProvincesResponse>("/api/v1/provinces", { quarter, horizon }, { auth: false }),
    staleTime: HOUR,
  });
}

export function useMunicipalities(provinceId: string | null, quarter?: string) {
  return useQuery({
    queryKey: ["municipalities", provinceId, quarter],
    queryFn: () =>
      api.get<MunicipalitiesResponse>(`/api/v1/provinces/${provinceId}/municipalities`, { quarter }, { auth: false }),
    enabled: !!provinceId,
    staleTime: HOUR,
  });
}

export function useForecast(scope: Scope, id: string, quarter?: string, horizon: Horizon = "nowcast") {
  return useQuery({
    queryKey: ["forecast", scope, id, quarter, horizon],
    queryFn: () => api.get<ForecastResponse>("/api/v1/forecast", { scope, id, quarter, horizon }, { auth: false }),
    enabled: !!id,
    staleTime: HOUR,
    retry: false, // a 404 (forecast_not_found / forecast_withheld) is a real answer, not a transient failure
  });
}

export function useTimeseries(
  scope: Scope,
  id: string,
  from?: string,
  to?: string,
  horizon: Horizon = "nowcast"
) {
  return useQuery({
    queryKey: ["timeseries", scope, id, from, to, horizon],
    queryFn: () =>
      api.get<TimeseriesResponse>("/api/v1/forecast/timeseries", { scope, id, from, to, horizon }, { auth: false }),
    enabled: !!id,
    staleTime: HOUR,
  });
}

export function useExplainability(scope: Scope, id: string, quarter?: string) {
  return useQuery({
    queryKey: ["explainability", scope, id, quarter],
    queryFn: () => api.get<ExplainabilityResponse>("/api/v1/explainability", { scope, id, quarter }, { auth: false }),
    enabled: !!id,
    staleTime: HOUR,
  });
}

export function useNews(scope: Scope, id: string, quarter?: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["news", scope, id, quarter, page, pageSize],
    queryFn: () => api.get<NewsResponse>("/api/v1/news", { scope, id, quarter, page, pageSize }, { auth: false }),
    enabled: !!id,
    staleTime: HOUR,
  });
}

export function useSearch(q: string) {
  return useQuery({
    queryKey: ["search", q],
    queryFn: () => api.get<SearchResponse>("/api/v1/search", { q, limit: 10 }, { auth: false }),
    enabled: q.trim().length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRejections(quarter?: string) {
  return useQuery({
    queryKey: ["rejections", quarter],
    queryFn: () => api.get<RejectionsResponse>("/api/v1/rejections", { quarter }, { auth: false }),
    staleTime: 60 * 1000, // short: an admin action elsewhere should be visible reasonably soon
  });
}

// ---------------------------------------------------------------------------
// Admin — review pipeline
// ---------------------------------------------------------------------------

export function useReviewQueue(quarter?: string, status?: string) {
  return useQuery({
    queryKey: ["admin", "review", quarter, status],
    queryFn: () => api.get<ReviewListResponse>("/api/v1/admin/review", { quarter, status }),
  });
}

function useInvalidateReviewAndPublic() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["admin", "review"] });
    qc.invalidateQueries({ queryKey: ["rejections"] });
    qc.invalidateQueries({ queryKey: ["provinces"] });
    qc.invalidateQueries({ queryKey: ["forecast"] });
    qc.invalidateQueries({ queryKey: ["timeseries"] });
  };
}

export function useApproveReview() {
  const invalidate = useInvalidateReviewAndPublic();
  return useMutation({
    mutationFn: (itemId: string) => api.post<ReviewItem>(`/api/v1/admin/review/${itemId}/approve`),
    onSuccess: invalidate,
  });
}

export function useRejectReview() {
  const invalidate = useInvalidateReviewAndPublic();
  return useMutation({
    mutationFn: ({ itemId, reason, notes }: { itemId: string; reason: string; notes?: string }) =>
      api.post<ReviewItem>(`/api/v1/admin/review/${itemId}/reject`, { reason, notes }),
    onSuccess: invalidate,
  });
}

export function useUndoReview() {
  const invalidate = useInvalidateReviewAndPublic();
  return useMutation({
    mutationFn: (itemId: string) => api.post<ReviewItem>(`/api/v1/admin/review/${itemId}/undo`),
    onSuccess: invalidate,
  });
}

export function useRestoreRejection() {
  const invalidate = useInvalidateReviewAndPublic();
  return useMutation({
    mutationFn: ({ provinceId, quarter }: { provinceId: string; quarter: string }) =>
      api.delete<ReviewItem>(`/api/v1/admin/rejections/${provinceId}/${quarter}`),
    onSuccess: invalidate,
  });
}

export function useAudit(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ["admin", "audit", page, pageSize],
    queryFn: () => api.get<AuditResponse>("/api/v1/admin/audit", { page, pageSize }),
  });
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export function useSubmitFeedback() {
  return useMutation({
    mutationFn: (body: FeedbackSubmitBody) => api.post<FeedbackCreated>("/api/v1/feedback", body, { auth: false }),
  });
}

export function useAdminFeedback(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: ["admin", "feedback", page, pageSize],
    queryFn: () => api.get<FeedbackListResponse>("/api/v1/admin/feedback", { page, pageSize }),
  });
}
