import { useMemo } from "react";
import { Card } from "../ui/Card";
import { Pill, StatusDot } from "../ui/Pill";
import type { StatsResponse } from "../../lib/types";

interface MitreHeatmapProps {
  stats: StatsResponse | null;
}

// Canonical ordering follows the kill-chain progression.
const TACTICS: { name: string; description: string; trigger: string }[] = [
  {
    name: "Initial Access",
    description: "Adversary trying to get into the network",
    trigger: "≥5 logon_failure from same src within 60s",
  },
  {
    name: "Persistence",
    description: "Maintaining foothold across restarts",
    trigger: "service_install or scheduled_task_create",
  },
  {
    name: "Lateral Movement",
    description: "Pivoting through the environment",
    trigger: "logon where src ≠ dest and dest is RFC1918",
  },
  {
    name: "Command and Control",
    description: "Communicating with compromised systems",
    trigger: "dest_port ∈ {4444, 6667, 1337, 8080}",
  },
  {
    name: "Exfiltration",
    description: "Stealing data out of the environment",
    trigger: "bytes_out > 10MB AND dest is non-RFC1918",
  },
];

// Match backend normalization (Command and Control vs Command & Control).
const NORMALIZE: Record<string, string> = {
  "command & control": "Command and Control",
  "c&c": "Command and Control",
  "command and control": "Command and Control",
};

function normalize(tactic: string): string {
  const key = tactic.trim().toLowerCase();
  return NORMALIZE[key] ?? tactic.trim();
}

// Log-ish color ramp: no hits = panel, then soft indigo → warning → danger → crimson.
function intensityStyle(count: number, max: number): {
  background: string;
  border: string;
  glow: string;
} {
  if (count === 0) {
    return {
      background: "rgba(255,255,255,0.02)",
      border: "rgba(255,255,255,0.06)",
      glow: "none",
    };
  }
  // Normalize on a log scale so a handful of events still lights up.
  const ratio = Math.min(1, Math.log10(count + 1) / Math.log10(Math.max(max, 10) + 1));
  if (ratio < 0.25) {
    return {
      background: "rgba(113,112,255,0.10)",
      border: "rgba(113,112,255,0.35)",
      glow: "0 0 12px rgba(113,112,255,0.15)",
    };
  }
  if (ratio < 0.5) {
    return {
      background: "rgba(245,166,35,0.12)",
      border: "rgba(245,166,35,0.40)",
      glow: "0 0 14px rgba(245,166,35,0.18)",
    };
  }
  if (ratio < 0.8) {
    return {
      background: "rgba(239,68,68,0.14)",
      border: "rgba(239,68,68,0.45)",
      glow: "0 0 16px rgba(239,68,68,0.22)",
    };
  }
  return {
    background: "rgba(220,38,38,0.22)",
    border: "rgba(220,38,38,0.65)",
    glow: "0 0 20px rgba(220,38,38,0.35)",
  };
}

export function MitreHeatmap({ stats }: MitreHeatmapProps) {
  const { counts, max, coverage, total } = useMemo(() => {
    const counts = new Map<string, number>();
    TACTICS.forEach((t) => counts.set(t.name, 0));
    for (const row of stats?.by_mitre_tactic ?? []) {
      const key = normalize(row.tactic);
      if (counts.has(key)) counts.set(key, (counts.get(key) ?? 0) + row.count);
    }
    let max = 0;
    let total = 0;
    let coverage = 0;
    counts.forEach((c) => {
      if (c > max) max = c;
      total += c;
      if (c > 0) coverage += 1;
    });
    return { counts, max, coverage, total };
  }, [stats]);

  const allCovered = coverage === TACTICS.length;

  return (
    <Card
      title="MITRE ATT&CK coverage"
      subtitle={`${total.toLocaleString()} tactic hits • ${coverage} of ${TACTICS.length} tactics triggered`}
      action={
        <Pill variant={allCovered ? "success" : "warning"}>
          <StatusDot variant={allCovered ? "success" : "warning"} />
          {allCovered ? "Full coverage" : `${coverage}/${TACTICS.length}`}
        </Pill>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-5 gap-2.5">
        {TACTICS.map((tactic) => {
          const count = counts.get(tactic.name) ?? 0;
          const style = intensityStyle(count, max);
          const dormant = count === 0;
          return (
            <div
              key={tactic.name}
              title={`${tactic.name}\n${tactic.description}\nRule: ${tactic.trigger}`}
              className="rounded-sm p-3 flex flex-col gap-2 transition-colors"
              style={{
                backgroundColor: style.background,
                border: `1px solid ${style.border}`,
                boxShadow: style.glow,
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={
                    "text-tiny font-medium uppercase tracking-wider " +
                    (dormant ? "text-fg-quaternary" : "text-fg-secondary")
                  }
                >
                  {tactic.name}
                </span>
                <span
                  className={
                    "w-1.5 h-1.5 rounded-full " +
                    (dormant ? "bg-fg-quaternary/40" : "bg-status-danger")
                  }
                  style={
                    !dormant
                      ? { boxShadow: "0 0 6px rgba(239,68,68,0.7)" }
                      : undefined
                  }
                />
              </div>
              <div
                className={
                  "text-h2 font-semibold leading-none " +
                  (dormant ? "text-fg-quaternary" : "text-fg-primary")
                }
                style={{
                  fontFeatureSettings: '"cv01", "ss03"',
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {count.toLocaleString()}
              </div>
              <div className="text-tiny text-fg-tertiary leading-snug">
                {tactic.description}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex items-center justify-between text-tiny text-fg-quaternary">
        <span>
          Intensity scales logarithmically with hit count — dormant tactics stay muted.
        </span>
        <div className="flex items-center gap-1.5">
          <span>low</span>
          <Swatch color="rgba(113,112,255,0.45)" />
          <Swatch color="rgba(245,166,35,0.55)" />
          <Swatch color="rgba(239,68,68,0.65)" />
          <Swatch color="rgba(220,38,38,0.85)" />
          <span>high</span>
        </div>
      </div>
    </Card>
  );
}

function Swatch({ color }: { color: string }) {
  return (
    <span
      className="w-3 h-2 rounded-[2px]"
      style={{ backgroundColor: color }}
    />
  );
}
