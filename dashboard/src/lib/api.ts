import axios from "axios";
import type {
  EventListResponse,
  EventsQueryParams,
  JobResponse,
  SourcetypeListResponse,
  StatsResponse,
  TimeseriesResponse,
  ValidateRequest,
  ValidateResponse,
} from "./types";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

export async function fetchStats(): Promise<StatsResponse> {
  const { data } = await api.get<StatsResponse>("/events/stats");
  return data;
}

export async function fetchTimeseries(params: {
  bucket_minutes?: number;
  window_hours?: number;
  sourcetype?: string;
}): Promise<TimeseriesResponse> {
  const { data } = await api.get<TimeseriesResponse>("/events/timeseries", {
    params,
  });
  return data;
}

export async function fetchEvents(
  params: EventsQueryParams = {},
): Promise<EventListResponse> {
  const { data } = await api.get<EventListResponse>("/events", { params });
  return data;
}

export async function fetchJob(jobId: string): Promise<JobResponse> {
  const { data } = await api.get<JobResponse>(`/jobs/${jobId}`);
  return data;
}

export async function fetchJobs(limit = 20): Promise<JobResponse[]> {
  const { data } = await api.get<JobResponse[]>("/jobs", { params: { limit } });
  return data;
}

export async function fetchSourcetypes(): Promise<SourcetypeListResponse> {
  const { data } = await api.get<SourcetypeListResponse>("/sourcetypes");
  return data;
}

export async function postValidate(
  payload: ValidateRequest,
): Promise<ValidateResponse> {
  const { data } = await api.post<ValidateResponse>("/validate", payload);
  return data;
}

export async function postIngest(
  sourcetype: string,
  lines: string[],
): Promise<{ job_id: string; status: string; total_lines: number }> {
  const { data } = await api.post("/ingest", { sourcetype, lines });
  return data;
}
