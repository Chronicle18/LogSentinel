import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../ui/Card";
import type { StatsResponse } from "../../lib/types";

interface SeverityChartProps {
  stats: StatsResponse | null;
}

const SEVERITY_ORDER = ["low", "medium", "high", "critical"] as const;
const SEVERITY_COLOR: Record<string, string> = {
  low: "#10b981",
  medium: "#f5a623",
  high: "#ef4444",
  critical: "#dc2626",
};

export function SeverityChart({ stats }: SeverityChartProps) {
  const data = useMemo(() => {
    if (!stats) return [];
    const map = new Map(stats.by_severity.map((s) => [s.severity, s.count]));
    return SEVERITY_ORDER.map((sev) => ({
      severity: sev,
      count: map.get(sev) ?? 0,
    }));
  }, [stats]);

  const total = data.reduce((a, b) => a + b.count, 0);

  return (
    <Card
      title="Severity distribution"
      subtitle={`${total.toLocaleString()} events with severity assigned`}
    >
      <div className="grid grid-cols-4 gap-2 mb-4">
        {data.map((d) => (
          <div
            key={d.severity}
            className="rounded-sm border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.02)] px-2.5 py-2"
          >
            <div className="flex items-center gap-1.5 text-tiny text-fg-tertiary capitalize">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: SEVERITY_COLOR[d.severity] }}
              />
              {d.severity}
            </div>
            <div
              className="text-h3 font-semibold text-fg-primary mt-0.5"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {d.count.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      <div className="h-[180px] -mx-1">
        {total === 0 ? (
          <div className="h-full flex items-center justify-center text-caption text-fg-tertiary">
            No severity data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              margin={{ top: 8, right: 8, left: -8, bottom: 0 }}
              barCategoryGap="30%"
            >
              <CartesianGrid
                vertical={false}
                strokeDasharray="2 4"
                stroke="rgba(255,255,255,0.05)"
              />
              <XAxis
                dataKey="severity"
                tickLine={false}
                axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
                tick={{ fontSize: 11, fill: "#8a8f98" }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: "#8a8f98" }}
                width={40}
              />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.03)" }}
                formatter={(value) => Number(value).toLocaleString()}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.map((d) => (
                  <Cell key={d.severity} fill={SEVERITY_COLOR[d.severity]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
