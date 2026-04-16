import { useMemo } from "react";
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../ui/Card";
import { Pill, StatusDot } from "../ui/Pill";
import { useTimeseries } from "../../hooks/useTimeseries";
import type { StatsResponse } from "../../lib/types";

interface ErrorRatePanelProps {
  stats: StatsResponse | null;
}

const THRESHOLD = 5;

export function ErrorRatePanel({ stats }: ErrorRatePanelProps) {
  const { data } = useTimeseries({ bucket_minutes: 5, window_hours: 24 });

  const trend = useMemo(() => {
    if (!data) return [];
    return data.points.map((p) => ({
      time: new Date(p.t).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      rate: p.total > 0 ? Number(((p.errors / p.total) * 100).toFixed(2)) : 0,
    }));
  }, [data]);

  const current = stats?.error_rate ?? 0;
  const over = current >= THRESHOLD;

  return (
    <Card
      title="Parse error rate"
      subtitle="Last 24h • 5-min buckets"
      action={
        <Pill variant={over ? "danger" : "success"}>
          <StatusDot variant={over ? "danger" : "success"} />
          {over ? "Above threshold" : "Healthy"}
        </Pill>
      }
    >
      <div className="flex items-baseline gap-3 mb-2">
        <div
          className={
            "text-display font-semibold leading-none " +
            (over ? "text-status-danger" : "text-fg-primary")
          }
          style={{
            fontFeatureSettings: '"cv01", "ss03"',
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {current.toFixed(2)}%
        </div>
        <div className="flex flex-col text-caption text-fg-tertiary">
          <span>
            <span className="text-fg-secondary font-mono tabular-nums">
              {(stats?.total_parse_errors ?? 0).toLocaleString()}
            </span>{" "}
            errors
          </span>
          <span>
            of{" "}
            <span className="text-fg-secondary font-mono tabular-nums">
              {(stats?.total_events ?? 0).toLocaleString()}
            </span>{" "}
            events
          </span>
        </div>
      </div>

      <div className="text-tiny text-fg-tertiary mb-2">
        Target threshold:{" "}
        <span className="text-fg-secondary font-mono">{THRESHOLD}%</span>
      </div>

      <div className="h-[120px] -mx-1">
        {trend.length === 0 ? (
          <div className="h-full flex items-center justify-center text-caption text-fg-tertiary">
            No data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={trend}
              margin={{ top: 8, right: 8, left: -8, bottom: 0 }}
            >
              <XAxis
                dataKey="time"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10, fill: "#62666d" }}
                minTickGap={40}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 10, fill: "#62666d" }}
                width={32}
                domain={[0, (dataMax: number) => Math.max(dataMax, THRESHOLD + 1)]}
                unit="%"
              />
              <ReferenceLine
                y={THRESHOLD}
                stroke="#ef4444"
                strokeDasharray="3 3"
                strokeWidth={1}
                label={{
                  value: `${THRESHOLD}%`,
                  fill: "#ef4444",
                  fontSize: 10,
                  position: "right",
                }}
              />
              <Tooltip cursor={{ stroke: "rgba(255,255,255,0.12)" }} />
              <Line
                type="monotone"
                dataKey="rate"
                stroke={over ? "#ef4444" : "#7170ff"}
                strokeWidth={1.75}
                dot={false}
                name="Error rate"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
