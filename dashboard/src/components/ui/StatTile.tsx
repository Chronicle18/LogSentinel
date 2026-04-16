import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

interface StatTileProps {
  label: string;
  value: string | number;
  sublabel?: string;
  trend?: "up" | "down" | "flat";
  accent?: "default" | "success" | "warning" | "danger" | "brand";
  icon?: ReactNode;
}

const ACCENT_COLOR: Record<NonNullable<StatTileProps["accent"]>, string> = {
  default: "text-fg-primary",
  success: "text-status-emerald",
  warning: "text-status-warning",
  danger: "text-status-danger",
  brand: "text-brand-violet",
};

export function StatTile({
  label,
  value,
  sublabel,
  accent = "default",
  icon,
}: StatTileProps) {
  return (
    <div
      className={cn(
        "bg-[rgba(255,255,255,0.02)]",
        "border border-[rgba(255,255,255,0.08)]",
        "rounded-card px-4 py-3.5",
        "flex flex-col gap-1",
      )}
    >
      <div className="flex items-center gap-1.5 text-fg-tertiary">
        {icon}
        <span className="text-tiny font-medium uppercase tracking-wider">
          {label}
        </span>
      </div>
      <div
        className={cn(
          "text-h2 font-semibold leading-none mt-1",
          ACCENT_COLOR[accent],
        )}
        style={{ fontFeatureSettings: '"cv01", "ss03"', fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </div>
      {sublabel && (
        <div className="text-caption text-fg-tertiary mt-1">{sublabel}</div>
      )}
    </div>
  );
}
