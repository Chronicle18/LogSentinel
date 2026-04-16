import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

interface CardProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

/** Linear-styled card: translucent white surface, standard 1px border, 8px radius. */
export function Card({
  title,
  subtitle,
  action,
  children,
  className,
  bodyClassName,
}: CardProps) {
  return (
    <div
      className={cn(
        "bg-[rgba(255,255,255,0.02)]",
        "border border-[rgba(255,255,255,0.08)]",
        "rounded-card",
        "shadow-ring-1",
        className,
      )}
    >
      {(title || action) && (
        <div className="flex items-start justify-between gap-4 px-5 pt-4 pb-3">
          <div className="min-w-0">
            {title && (
              <h3
                className="text-h3 font-semibold text-fg-primary"
                style={{ fontFeatureSettings: '"cv01", "ss03"' }}
              >
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-caption text-fg-tertiary mt-1">{subtitle}</p>
            )}
          </div>
          {action && <div className="flex-shrink-0">{action}</div>}
        </div>
      )}
      <div className={cn("px-5 pb-5", !title && "pt-5", bodyClassName)}>
        {children}
      </div>
    </div>
  );
}
