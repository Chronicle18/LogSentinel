import { useMemo, useState } from "react";
import { Card } from "../ui/Card";
import { Pill, StatusDot } from "../ui/Pill";
import { useEvents } from "../../hooks/useEvents";
import type { EventRow, Severity, SourcetypeInfo } from "../../lib/types";
import { EventDetailDrawer } from "./EventDetailDrawer";

interface EventTableProps {
  sourcetypes: SourcetypeInfo[];
}

const SEVERITIES: Severity[] = ["low", "medium", "high", "critical"];
const PAGE_SIZE = 25;

const SEVERITY_VARIANT: Record<Severity, "success" | "warning" | "danger" | "critical"> =
  {
    low: "success",
    medium: "warning",
    high: "danger",
    critical: "critical",
  };

export function EventTable({ sourcetypes }: EventTableProps) {
  const [sourcetype, setSourcetype] = useState<string | undefined>(undefined);
  const [severity, setSeverity] = useState<Severity | undefined>(undefined);
  const [src, setSrc] = useState<string>("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<EventRow | null>(null);

  const params = useMemo(
    () => ({
      sourcetype,
      severity,
      src: src.trim() || undefined,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [sourcetype, severity, src, page],
  );

  const { data, error } = useEvents(params);
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
    <EventDetailDrawer event={selected} onClose={() => setSelected(null)} />
    <Card
      title="Events"
      subtitle={`${total.toLocaleString()} results • page ${page + 1} of ${totalPages}`}
      action={
        <Pill variant="info">
          <StatusDot variant="brand" />
          Live
        </Pill>
      }
      bodyClassName="!px-0 !pb-0"
    >
      <div className="px-5 pb-3 flex flex-wrap gap-2 items-center">
        <Select
          value={sourcetype ?? ""}
          onChange={(v) => {
            setSourcetype(v || undefined);
            setPage(0);
          }}
          options={[
            { value: "", label: "All sourcetypes" },
            ...sourcetypes.map((s) => ({
              value: s.sourcetype,
              label: s.sourcetype,
            })),
          ]}
        />
        <Select
          value={severity ?? ""}
          onChange={(v) => {
            setSeverity((v as Severity) || undefined);
            setPage(0);
          }}
          options={[
            { value: "", label: "Any severity" },
            ...SEVERITIES.map((s) => ({ value: s, label: s })),
          ]}
        />
        <input
          value={src}
          onChange={(e) => {
            setSrc(e.target.value);
            setPage(0);
          }}
          placeholder="src IP filter…"
          className="h-7 px-2.5 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.08)] rounded-md text-tiny text-fg-primary placeholder:text-fg-quaternary focus:outline-none focus:border-[rgba(113,112,255,0.4)] font-mono w-[180px]"
        />
        {error && (
          <span className="text-tiny text-status-danger ml-auto">{error}</span>
        )}
      </div>

      <div className="overflow-x-auto border-t border-[rgba(255,255,255,0.05)]">
        <table className="w-full text-tiny">
          <thead className="bg-[rgba(255,255,255,0.02)]">
            <tr className="text-fg-tertiary">
              <Th>Time</Th>
              <Th>Sourcetype</Th>
              <Th>Severity</Th>
              <Th>Src</Th>
              <Th>Dest</Th>
              <Th>User</Th>
              <Th>Action</Th>
              <Th>MITRE</Th>
            </tr>
          </thead>
          <tbody>
            {data?.events.map((e) => (
              <EventRowCells
                key={e.id}
                ev={e}
                onClick={() => setSelected(e)}
              />
            ))}
            {(!data || data.events.length === 0) && (
              <tr>
                <td
                  colSpan={8}
                  className="py-10 text-center text-fg-tertiary"
                >
                  No events match the filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="px-5 py-3 flex items-center justify-between border-t border-[rgba(255,255,255,0.05)]">
        <span className="text-tiny text-fg-tertiary">
          Showing{" "}
          <span className="text-fg-secondary font-mono tabular-nums">
            {data?.events.length ?? 0}
          </span>{" "}
          of{" "}
          <span className="text-fg-secondary font-mono tabular-nums">
            {total.toLocaleString()}
          </span>
        </span>
        <div className="flex gap-1.5">
          <PageBtn
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            ← Prev
          </PageBtn>
          <PageBtn
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Next →
          </PageBtn>
        </div>
      </div>
    </Card>
    </>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left px-3 py-2 font-medium uppercase tracking-wider text-micro">
      {children}
    </th>
  );
}

function EventRowCells({ ev, onClick }: { ev: EventRow; onClick: () => void }) {
  const sev = ev.severity;
  const tactics = (ev.mitre_tactic ?? "").split(",").filter(Boolean);
  return (
    <tr
      onClick={onClick}
      className="border-t border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.03)] transition-colors cursor-pointer">
      <td className="px-3 py-2 text-fg-secondary font-mono tabular-nums whitespace-nowrap">
        {new Date(ev._time).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}
      </td>
      <td className="px-3 py-2 text-fg-secondary whitespace-nowrap">
        {ev.sourcetype}
      </td>
      <td className="px-3 py-2">
        {sev ? (
          <Pill variant={SEVERITY_VARIANT[sev]}>{sev}</Pill>
        ) : ev.parse_error ? (
          <Pill variant="danger">parse error</Pill>
        ) : (
          <span className="text-fg-quaternary">—</span>
        )}
      </td>
      <td className="px-3 py-2 text-fg-secondary font-mono truncate max-w-[140px]">
        {ev.src ?? "—"}
      </td>
      <td className="px-3 py-2 text-fg-secondary font-mono truncate max-w-[140px]">
        {ev.dest ?? "—"}
      </td>
      <td className="px-3 py-2 text-fg-secondary truncate max-w-[120px]">
        {ev.user ?? "—"}
      </td>
      <td className="px-3 py-2 text-fg-secondary truncate max-w-[140px]">
        {ev.action ?? "—"}
      </td>
      <td className="px-3 py-2">
        {tactics.length > 0 ? (
          <div className="flex gap-1 flex-wrap">
            {tactics.slice(0, 2).map((t) => (
              <Pill key={t} variant="brand">
                {t.trim()}
              </Pill>
            ))}
            {tactics.length > 2 && (
              <span className="text-tiny text-fg-tertiary">
                +{tactics.length - 2}
              </span>
            )}
          </div>
        ) : (
          <span className="text-fg-quaternary">—</span>
        )}
      </td>
    </tr>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-7 px-2 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.08)] rounded-md text-tiny text-fg-primary focus:outline-none focus:border-[rgba(113,112,255,0.4)]"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-bg-surface">
          {o.label}
        </option>
      ))}
    </select>
  );
}

function PageBtn({
  children,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={
        "h-7 px-3 rounded-md border text-tiny font-medium transition-colors " +
        (disabled
          ? "border-[rgba(255,255,255,0.04)] text-fg-quaternary cursor-not-allowed"
          : "border-[rgba(255,255,255,0.08)] text-fg-secondary hover:bg-[rgba(255,255,255,0.04)]")
      }
    >
      {children}
    </button>
  );
}
