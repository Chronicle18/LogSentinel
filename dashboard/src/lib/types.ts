// Mirrors api/schemas.py response models

export type Severity = "low" | "medium" | "high" | "critical";
export type JobStatus = "queued" | "processing" | "complete" | "failed";

export interface EventRow {
  id: number;
  _time: string;
  sourcetype: string;
  src: string | null;
  dest: string | null;
  user: string | null;
  action: string | null;
  severity: Severity | null;
  mitre_tactic: string | null;
  parse_error: boolean;
  raw: string | null;
  job_id: string | null;
}

export interface EventListResponse {
  total: number;
  events: EventRow[];
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  sourcetype: string | null;
  total_lines: number;
  processed_lines: number;
  error_count: number;
  progress_pct: number;
  created_at: string;
  updated_at: string;
}

export interface SourcetypeCount {
  sourcetype: string;
  count: number;
}
export interface SeverityCount {
  severity: string;
  count: number;
}
export interface MitreTacticCount {
  tactic: string;
  count: number;
}

export interface StatsResponse {
  total_events: number;
  total_parse_errors: number;
  error_rate: number;
  by_sourcetype: SourcetypeCount[];
  by_severity: SeverityCount[];
  by_mitre_tactic: MitreTacticCount[];
}

export interface SourcetypeInfo {
  sourcetype: string;
  rule_count: number;
  config_path: string | null;
}

export interface SourcetypeListResponse {
  sourcetypes: SourcetypeInfo[];
}

export interface TimeseriesPoint {
  t: string;
  total: number;
  errors: number;
}

export interface TimeseriesResponse {
  bucket_minutes: number;
  window_hours: number;
  sourcetype: string | null;
  points: TimeseriesPoint[];
}

export interface ValidateRequest {
  sourcetype: string;
  line: string;
}

export interface ValidateResponse {
  populated_fields: string[];
  missing_fields: string[];
  verdict: "pass" | "fail";
  event: Record<string, string | null>;
}

export interface EventsQueryParams {
  sourcetype?: string;
  severity?: Severity;
  src?: string;
  action?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}
