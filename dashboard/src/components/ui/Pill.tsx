import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

type PillVariant =
  | "neutral"
  | "success"
  | "warning"
  | "danger"
  | "critical"
  | "brand"
  | "info";

interface PillProps {
  variant?: PillVariant;
  children: ReactNode;
  className?: string;
}

const VARIANT_STYLES: Record<PillVariant, string> = {
  neutral:
    "border-[#23252a] text-fg-secondary bg-transparent",
  success:
    "border-[rgba(39,166,68,0.35)] text-[#5eddb5] bg-[rgba(16,185,129,0.08)]",
  warning:
    "border-[rgba(245,166,35,0.35)] text-[#f5c773] bg-[rgba(245,166,35,0.08)]",
  danger:
    "border-[rgba(239,68,68,0.35)] text-[#ff8b8b] bg-[rgba(239,68,68,0.08)]",
  critical:
    "border-[rgba(220,38,38,0.5)] text-[#ff7676] bg-[rgba(220,38,38,0.12)]",
  brand:
    "border-[rgba(113,112,255,0.4)] text-[#a2a8ff] bg-[rgba(113,112,255,0.1)]",
  info: "border-[rgba(122,127,173,0.4)] text-[#a9adcc] bg-[rgba(122,127,173,0.08)]",
};

export function Pill({ variant = "neutral", children, className }: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5",
        "h-[22px] px-2.5",
        "rounded-pill border",
        "text-tiny font-medium",
        "whitespace-nowrap",
        VARIANT_STYLES[variant],
        className,
      )}
      style={{ fontFeatureSettings: '"cv01", "ss03"' }}
    >
      {children}
    </span>
  );
}

/** Small colored dot used for status indicators. */
export function StatusDot({
  variant = "neutral",
}: {
  variant?: PillVariant;
}) {
  const colors: Record<PillVariant, string> = {
    neutral: "bg-fg-tertiary",
    success: "bg-status-emerald",
    warning: "bg-status-warning",
    danger: "bg-status-danger",
    critical: "bg-status-critical",
    brand: "bg-brand-violet",
    info: "bg-brand-lavender",
  };
  return (
    <span
      className={cn("inline-block w-1.5 h-1.5 rounded-full", colors[variant])}
    />
  );
}
