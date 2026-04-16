import { Card } from "../ui/Card";
import { Pill, StatusDot } from "../ui/Pill";
import { useJobs } from "../../hooks/useJobs";
import type { JobResponse, JobStatus } from "../../lib/types";

const STATUS_META: Record<
  JobStatus,
  { variant: "neutral" | "brand" | "success" | "danger"; label: string }
> = {
  queued: { variant: "neutral", label: "Queued" },
  processing: { variant: "brand", label: "Processing" },
  complete: { variant: "success", label: "Complete" },
  failed: { variant: "danger", label: "Failed" },
};

export function JobTracker() {
  const { data, error } = useJobs(8);

  return (
    <Card
      title="Recent jobs"
      subtitle="Polling every 2s • last 8 jobs"
      action={
        <Pill variant="info">
          <StatusDot variant="brand" />
          Live
        </Pill>
      }
    >
      {error ? (
        <div className="text-caption text-fg-tertiary py-8 text-center">
          {error}
        </div>
      ) : !data || data.length === 0 ? (
        <div className="text-caption text-fg-tertiary py-8 text-center">
          No jobs yet. POST to <code className="text-fg-secondary">/ingest</code>{" "}
          to kick one off.
        </div>
      ) : (
        <ul className="flex flex-col divide-y divide-[rgba(255,255,255,0.05)]">
          {data.map((job) => (
            <JobRow key={job.job_id} job={job} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function JobRow({ job }: { job: JobResponse }) {
  const meta = STATUS_META[job.status];
  const active = job.status === "processing" || job.status === "queued";
  const progress = Math.min(100, Math.max(0, job.progress_pct));

  return (
    <li className="py-3 flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Pill variant={meta.variant}>
            <StatusDot variant={meta.variant} />
            {meta.label}
          </Pill>
          <span className="text-caption text-fg-secondary font-medium">
            {job.sourcetype ?? "—"}
          </span>
          <span
            className="text-tiny font-mono text-fg-quaternary truncate"
            title={job.job_id}
          >
            {job.job_id.slice(0, 8)}
          </span>
        </div>

        <div className="mt-2 h-1.5 rounded-pill bg-[rgba(255,255,255,0.04)] overflow-hidden">
          <div
            className={
              "h-full transition-all duration-500 " +
              (job.status === "failed"
                ? "bg-status-danger"
                : job.status === "complete"
                  ? "bg-status-emerald"
                  : "bg-gradient-to-r from-brand-indigo to-brand-violet")
            }
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mt-1.5 flex items-center justify-between text-tiny text-fg-tertiary font-mono tabular-nums">
          <span>
            {job.processed_lines.toLocaleString()} /{" "}
            {job.total_lines.toLocaleString()} lines
            {job.error_count > 0 && (
              <span className="text-status-warning ml-2">
                · {job.error_count.toLocaleString()} errors
              </span>
            )}
          </span>
          <span>
            {active ? `${progress.toFixed(1)}%` : formatRelative(job.updated_at)}
          </span>
        </div>
      </div>
    </li>
  );
}

function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = Math.max(0, now - then);
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}
