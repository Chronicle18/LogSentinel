import { useState } from "react";
import axios from "axios";
import { Card } from "../ui/Card";
import { Pill, StatusDot } from "../ui/Pill";
import { postValidate } from "../../lib/api";
import type { SourcetypeInfo, ValidateResponse } from "../../lib/types";

interface ValidatorPanelProps {
  sourcetypes: SourcetypeInfo[];
}

// Required CIM fields per CLAUDE.md §5.
const REQUIRED_CIM_FIELDS = [
  "_time",
  "src",
  "dest",
  "user",
  "action",
  "severity",
  "sourcetype",
  "raw",
  "parse_error",
  "job_id",
] as const;

const SAMPLE_LINES: Record<string, string> = {
  syslog_auth:
    "Apr 15 08:23:11 host-01 sshd[1234]: Failed password for jdoe from 10.0.0.5",
  syslog_kern:
    "Apr 15 08:23:11 host-01 kernel: [12345.678] IN=eth0 SRC=10.0.0.5 DST=8.8.8.8 PROTO=TCP DPT=443",
  winevt_security:
    "<Event><EventID>4624</EventID><TimeCreated>2026-04-15 08:23:11</TimeCreated><TargetUserName>jdoe</TargetUserName><IpAddress>10.0.0.5</IpAddress></Event>",
  winevt_system:
    "<Event><EventID>7045</EventID><TimeCreated>2026-04-15 08:23:11</TimeCreated><ServiceName>MaliciousSvc</ServiceName></Event>",
  winevt_application:
    "<Event><EventID>1000</EventID><TimeCreated>2026-04-15 08:23:11</TimeCreated><Source>Application</Source><Message>Crash</Message></Event>",
};

export function ValidatorPanel({ sourcetypes }: ValidatorPanelProps) {
  const [sourcetype, setSourcetype] = useState<string>(
    sourcetypes[0]?.sourcetype ?? "",
  );
  const [line, setLine] = useState<string>("");
  const [result, setResult] = useState<ValidateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!sourcetype || !line.trim()) {
      setError("Provide a sourcetype and a log line.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await postValidate({ sourcetype, line });
      setResult(res);
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail;
        setError(
          typeof detail === "string"
            ? detail
            : detail?.detail ?? e.message ?? "Validation failed",
        );
      } else {
        setError(e instanceof Error ? e.message : "Validation failed");
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const loadSample = () => {
    const sample = SAMPLE_LINES[sourcetype];
    if (sample) setLine(sample);
  };

  const passed = result?.verdict === "pass";
  const populatedSet = new Set(result?.populated_fields ?? []);
  const populatedCount = REQUIRED_CIM_FIELDS.filter((f) =>
    populatedSet.has(f),
  ).length;

  return (
    <Card
      title="CIM compliance validator"
      subtitle="Paste a raw log line, see how the pipeline normalizes it"
      action={
        result ? (
          <Pill variant={passed ? "success" : "danger"}>
            <StatusDot variant={passed ? "success" : "danger"} />
            {passed ? "Pass" : "Fail"}
          </Pill>
        ) : (
          <Pill variant="neutral">Idle</Pill>
        )
      }
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2 items-center">
          <select
            value={sourcetype}
            onChange={(e) => setSourcetype(e.target.value)}
            className="h-7 px-2 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.08)] rounded-md text-tiny text-fg-primary focus:outline-none focus:border-[rgba(113,112,255,0.4)]"
          >
            {sourcetypes.map((s) => (
              <option
                key={s.sourcetype}
                value={s.sourcetype}
                className="bg-bg-surface"
              >
                {s.sourcetype}
              </option>
            ))}
          </select>
          <button
            onClick={loadSample}
            className="h-7 px-3 rounded-md border border-[rgba(255,255,255,0.08)] text-tiny font-medium text-fg-secondary hover:bg-[rgba(255,255,255,0.04)] transition-colors"
          >
            Load sample
          </button>
          <div className="flex-1" />
          <button
            onClick={submit}
            disabled={loading || !line.trim()}
            className={
              "h-7 px-4 rounded-md text-tiny font-medium transition-colors " +
              (loading || !line.trim()
                ? "bg-[rgba(255,255,255,0.04)] text-fg-quaternary cursor-not-allowed"
                : "bg-gradient-to-r from-brand-indigo to-brand-violet text-white hover:opacity-90")
            }
          >
            {loading ? "Validating…" : "Validate"}
          </button>
        </div>

        <textarea
          value={line}
          onChange={(e) => setLine(e.target.value)}
          placeholder="Paste a raw log line here…"
          rows={3}
          className="w-full px-3 py-2 bg-[rgba(0,0,0,0.25)] border border-[rgba(255,255,255,0.08)] rounded-md text-tiny text-fg-primary font-mono placeholder:text-fg-quaternary focus:outline-none focus:border-[rgba(113,112,255,0.4)] resize-y"
        />

        {error && (
          <div className="text-tiny text-status-danger bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.25)] rounded-sm px-3 py-2">
            {error}
          </div>
        )}

        {result && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
            <div>
              <div className="flex items-baseline justify-between mb-2">
                <h4 className="text-tiny font-medium uppercase tracking-wider text-fg-tertiary">
                  Required CIM fields
                </h4>
                <span className="text-tiny text-fg-quaternary">
                  {populatedCount} / {REQUIRED_CIM_FIELDS.length} populated
                </span>
              </div>
              <ul className="flex flex-col divide-y divide-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.06)] rounded-sm">
                {REQUIRED_CIM_FIELDS.map((field) => {
                  const populated = populatedSet.has(field);
                  const value = result.event[field];
                  return (
                    <li
                      key={field}
                      className="flex items-center gap-3 px-3 py-1.5 text-tiny"
                    >
                      <span
                        className={
                          "w-4 h-4 rounded-full flex items-center justify-center shrink-0 " +
                          (populated
                            ? "bg-[rgba(16,185,129,0.15)] text-status-emerald"
                            : "bg-[rgba(239,68,68,0.15)] text-status-danger")
                        }
                      >
                        {populated ? "✓" : "✗"}
                      </span>
                      <span
                        className={
                          "w-24 shrink-0 font-mono " +
                          (populated ? "text-fg-tertiary" : "text-fg-quaternary")
                        }
                      >
                        {field}
                      </span>
                      <span
                        className={
                          "flex-1 font-mono truncate " +
                          (populated ? "text-fg-secondary" : "text-fg-quaternary")
                        }
                        title={value ?? undefined}
                      >
                        {value ?? "—"}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className="flex flex-col gap-3">
              <div>
                <h4 className="text-tiny font-medium uppercase tracking-wider text-fg-tertiary mb-2">
                  Extraction summary
                </h4>
                <div className="border border-[rgba(255,255,255,0.06)] rounded-sm p-3 flex flex-col gap-1.5 text-tiny">
                  <Row
                    label="Verdict"
                    value={
                      <span
                        className={
                          "font-semibold " +
                          (passed ? "text-status-emerald" : "text-status-danger")
                        }
                      >
                        {passed ? "PASS" : "FAIL"}
                      </span>
                    }
                  />
                  <Row
                    label="Populated"
                    value={`${result.populated_fields.length} fields`}
                  />
                  <Row
                    label="Missing"
                    value={
                      <span
                        className={
                          result.missing_fields.length > 0
                            ? "text-status-warning"
                            : "text-fg-secondary"
                        }
                      >
                        {result.missing_fields.length === 0
                          ? "none"
                          : result.missing_fields.join(", ")}
                      </span>
                    }
                  />
                  <Row
                    label="Parse error"
                    value={
                      result.event.parse_error === "True" ||
                      result.event.parse_error === "true" ? (
                        <span className="text-status-danger">yes</span>
                      ) : (
                        <span className="text-status-emerald">no</span>
                      )
                    }
                  />
                </div>
              </div>

              <div>
                <h4 className="text-tiny font-medium uppercase tracking-wider text-fg-tertiary mb-2">
                  Additional extracted fields
                </h4>
                <div className="border border-[rgba(255,255,255,0.06)] rounded-sm p-3 max-h-[240px] overflow-y-auto">
                  {Object.entries(result.event)
                    .filter(
                      ([k]) =>
                        !(REQUIRED_CIM_FIELDS as readonly string[]).includes(k),
                    )
                    .map(([k, v]) => (
                      <div
                        key={k}
                        className="flex items-start gap-3 py-1 text-tiny"
                      >
                        <span className="w-28 shrink-0 font-mono text-fg-tertiary">
                          {k}
                        </span>
                        <span className="flex-1 font-mono text-fg-secondary break-all">
                          {v ?? "—"}
                        </span>
                      </div>
                    ))}
                  {Object.entries(result.event).filter(
                    ([k]) =>
                      !(REQUIRED_CIM_FIELDS as readonly string[]).includes(k),
                  ).length === 0 && (
                    <div className="text-tiny text-fg-quaternary italic">
                      No additional fields extracted.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 shrink-0 font-mono text-fg-tertiary">{label}</span>
      <span className="flex-1 font-mono text-fg-secondary">{value}</span>
    </div>
  );
}
