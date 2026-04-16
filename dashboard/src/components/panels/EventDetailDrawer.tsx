import { useEffect } from "react";
import { Pill, StatusDot } from "../ui/Pill";
import type { EventRow, Severity } from "../../lib/types";

interface EventDetailDrawerProps {
  event: EventRow | null;
  onClose: () => void;
}

const SEVERITY_VARIANT: Record<Severity, "success" | "warning" | "danger" | "critical"> =
  {
    low: "success",
    medium: "warning",
    high: "danger",
    critical: "critical",
  };

// 10 required CIM fields from CLAUDE.md §5.
const CIM_FIELDS: (keyof EventRow)[] = [
  "_time",
  "sourcetype",
  "src",
  "dest",
  "user",
  "action",
  "severity",
  "raw",
  "parse_error",
  "job_id",
];

const TACTIC_RULES: Record<string, string> = {
  "Initial Access": "≥5 logon_failure from same src within 60s",
  Persistence: "action ∈ {service_install, scheduled_task_create}",
  "Lateral Movement": "logon where src ≠ dest and dest is RFC1918",
  "Command & Control": "dest_port ∈ {4444, 6667, 1337, 8080}",
  "Command and Control": "dest_port ∈ {4444, 6667, 1337, 8080}",
  Exfiltration: "bytes_out > 10MB AND dest is non-RFC1918",
};

export function EventDetailDrawer({ event, onClose }: EventDetailDrawerProps) {
  useEffect(() => {
    if (!event) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [event, onClose]);

  if (!event) return null;

  const tactics = (event.mitre_tactic ?? "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <aside
        className="fixed top-0 right-0 bottom-0 w-full max-w-[480px] z-40 bg-bg-panel border-l border-[rgba(255,255,255,0.08)] shadow-2xl flex flex-col"
        style={{ boxShadow: "-8px 0 32px rgba(0,0,0,0.45)" }}
      >
        <header className="px-5 py-4 border-b border-[rgba(255,255,255,0.06)] flex items-center justify-between">
          <div>
            <h2
              className="text-body font-semibold text-fg-primary tracking-tight"
              style={{ fontFeatureSettings: '"cv01", "ss03"' }}
            >
              Event #{event.id}
            </h2>
            <p className="text-caption text-fg-tertiary mt-0.5 font-mono">
              {new Date(event._time).toLocaleString()}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="w-7 h-7 rounded-md flex items-center justify-center text-fg-tertiary hover:text-fg-primary hover:bg-[rgba(255,255,255,0.06)] transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto">
          {/* Status strip */}
          <div className="px-5 py-3 flex flex-wrap gap-2 border-b border-[rgba(255,255,255,0.04)]">
            {event.severity ? (
              <Pill variant={SEVERITY_VARIANT[event.severity]}>
                {event.severity}
              </Pill>
            ) : event.parse_error ? (
              <Pill variant="danger">
                <StatusDot variant="danger" />
                parse error
              </Pill>
            ) : (
              <Pill variant="neutral">no severity</Pill>
            )}
            <Pill variant="neutral">{event.sourcetype}</Pill>
            {tactics.map((t) => (
              <Pill key={t} variant="brand">
                {t}
              </Pill>
            ))}
          </div>

          {/* Raw log */}
          <Section title="Raw log line">
            <pre className="text-tiny font-mono text-fg-secondary bg-[rgba(0,0,0,0.3)] border border-[rgba(255,255,255,0.04)] rounded-sm p-3 whitespace-pre-wrap break-all leading-relaxed">
              {event.raw ?? "(no raw line stored)"}
            </pre>
          </Section>

          {/* CIM fields */}
          <Section
            title="CIM fields"
            subtitle={`${CIM_FIELDS.filter((f) => isPopulated(event[f])).length} of ${CIM_FIELDS.length} populated`}
          >
            <div className="flex flex-col divide-y divide-[rgba(255,255,255,0.04)]">
              {CIM_FIELDS.map((field) => {
                const val = event[field];
                const populated = isPopulated(val);
                return (
                  <div
                    key={field}
                    className="flex items-start py-2 gap-3 text-tiny"
                  >
                    <span
                      className={
                        "w-4 h-4 rounded-full flex items-center justify-center mt-0.5 shrink-0 " +
                        (populated
                          ? "bg-[rgba(16,185,129,0.15)] text-status-emerald"
                          : "bg-[rgba(255,255,255,0.04)] text-fg-quaternary")
                      }
                    >
                      {populated ? "✓" : "·"}
                    </span>
                    <span
                      className={
                        "w-28 shrink-0 font-mono " +
                        (populated ? "text-fg-tertiary" : "text-fg-quaternary")
                      }
                    >
                      {field}
                    </span>
                    <span
                      className={
                        "flex-1 font-mono break-all " +
                        (populated ? "text-fg-secondary" : "text-fg-quaternary")
                      }
                    >
                      {formatValue(val)}
                    </span>
                  </div>
                );
              })}
            </div>
          </Section>

          {/* MITRE reasoning */}
          {tactics.length > 0 && (
            <Section title="MITRE ATT&CK reasoning">
              <div className="flex flex-col gap-2">
                {tactics.map((t) => (
                  <div
                    key={t}
                    className="border border-[rgba(239,68,68,0.25)] bg-[rgba(239,68,68,0.06)] rounded-sm p-3"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-status-danger" />
                      <span className="text-caption font-semibold text-fg-primary">
                        {t}
                      </span>
                    </div>
                    <div className="text-tiny text-fg-tertiary font-mono leading-snug">
                      Rule: {TACTIC_RULES[t] ?? "(unknown trigger)"}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Job */}
          {event.job_id && (
            <Section title="Ingestion">
              <div className="text-tiny text-fg-tertiary">
                Job{" "}
                <span
                  className="font-mono text-fg-secondary"
                  title={event.job_id}
                >
                  {event.job_id}
                </span>
              </div>
            </Section>
          )}
        </div>
      </aside>
    </>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="px-5 py-4 border-b border-[rgba(255,255,255,0.04)]">
      <div className="flex items-baseline justify-between mb-2">
        <h3 className="text-tiny font-medium uppercase tracking-wider text-fg-tertiary">
          {title}
        </h3>
        {subtitle && (
          <span className="text-tiny text-fg-quaternary">{subtitle}</span>
        )}
      </div>
      {children}
    </section>
  );
}

function isPopulated(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string" && value.trim() === "") return false;
  if (typeof value === "boolean") return true;
  return true;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string" && value.length > 200) {
    return value.slice(0, 200) + "…";
  }
  return String(value);
}
