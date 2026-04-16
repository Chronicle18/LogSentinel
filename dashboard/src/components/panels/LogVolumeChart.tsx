import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../ui/Card";
import { Pill } from "../ui/Pill";
import { useTimeseries } from "../../hooks/useTimeseries";
import type { SourcetypeInfo } from "../../lib/types";

interface LogVolumeChartProps {
  sourcetypes: SourcetypeInfo[];
}

export function LogVolumeChart({ sourcetypes }: LogVolumeChartProps) {
  const [selected, setSelected] = useState<string | undefined>(undefined);
  const { data, error } = useTimeseries({
    bucket_minutes: 5,
    window_hours: 24,
    sourcetype: selected,
  });

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.points.map((p) => ({
      time: new Date(p.t).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      total: p.total,
      errors: p.errors,
    }));
  }, [data]);

  const total = chartData.reduce((a, b) => a + b.total, 0);

  return (
    <Card
      title="Log volume"
      subtitle={`5-minute buckets • last 24h${
        selected ? ` • ${selected}` : ""
      }`}
      action={
        <div className="flex items-center gap-2">
          <Pill variant="brand">{total.toLocaleString()} events</Pill>
        </div>
      }
    >
      <div className="flex flex-wrap gap-1.5 mb-4">
        <FilterChip
          label="All"
          active={!selected}
          onClick={() => setSelected(undefined)}
        />
        {sourcetypes.map((s) => (
          <FilterChip
            key={s.sourcetype}
            label={s.sourcetype}
            active={selected === s.sourcetype}
            onClick={() => setSelected(s.sourcetype)}
          />
        ))}
      </div>

      <div className="h-[260px] -mx-1">
        {error ? (
          <EmptyState message={error} />
        ) : chartData.length === 0 ? (
          <EmptyState message="No data in the selected window" />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 8, right: 8, left: -8, bottom: 0 }}
            >
              <defs>
                <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7170ff" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#7170ff" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="errorFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="2 4"
                vertical={false}
                stroke="rgba(255,255,255,0.05)"
              />
              <XAxis
                dataKey="time"
                tickLine={false}
                axisLine={{ stroke: "rgba(255,255,255,0.08)" }}
                tick={{ fontSize: 11, fill: "#8a8f98" }}
                minTickGap={32}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: "#8a8f98" }}
                width={40}
              />
              <Tooltip
                cursor={{ stroke: "rgba(255,255,255,0.12)", strokeWidth: 1 }}
              />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#7170ff"
                strokeWidth={1.5}
                fill="url(#volumeFill)"
                name="Events"
              />
              <Area
                type="monotone"
                dataKey="errors"
                stroke="#ef4444"
                strokeWidth={1.5}
                fill="url(#errorFill)"
                name="Parse errors"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "inline-flex items-center h-6 px-2.5 rounded-pill border text-tiny font-medium transition-colors " +
        (active
          ? "bg-[rgba(113,112,255,0.12)] border-[rgba(113,112,255,0.4)] text-[#a2a8ff]"
          : "bg-transparent border-[#23252a] text-fg-secondary hover:bg-[rgba(255,255,255,0.03)]")
      }
    >
      {label}
    </button>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="h-full flex items-center justify-center text-caption text-fg-tertiary">
      {message}
    </div>
  );
}
