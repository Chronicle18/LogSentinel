import { cn } from "../../lib/cn";

interface HeaderProps {
  apiStatus: "connected" | "disconnected" | "checking";
}

export function Header({ apiStatus }: HeaderProps) {
  const statusMap = {
    connected: {
      label: "API connected",
      dot: "bg-status-emerald",
      text: "text-fg-secondary",
    },
    disconnected: {
      label: "API offline",
      dot: "bg-status-danger",
      text: "text-fg-secondary",
    },
    checking: {
      label: "Connecting…",
      dot: "bg-fg-quaternary",
      text: "text-fg-tertiary",
    },
  } as const;
  const s = statusMap[apiStatus];

  return (
    <header
      className={cn(
        "sticky top-0 z-20",
        "bg-bg-panel/80 backdrop-blur",
        "border-b border-[rgba(255,255,255,0.05)]",
      )}
    >
      <div className="max-w-[1440px] mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Logo />
          <span
            className="text-body font-semibold text-fg-primary tracking-tight"
            style={{ fontFeatureSettings: '"cv01", "ss03"' }}
          >
            LogSentinel
          </span>
          <span className="text-tiny text-fg-quaternary font-mono ml-1.5">
            v1.0
          </span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span
              className={cn("w-1.5 h-1.5 rounded-full", s.dot)}
              style={
                apiStatus === "connected"
                  ? {
                      boxShadow: "0 0 8px rgba(16, 185, 129, 0.6)",
                    }
                  : undefined
              }
            />
            <span className={cn("text-caption", s.text)}>{s.label}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

function Logo() {
  return (
    <div
      className="w-6 h-6 rounded-sm flex items-center justify-center"
      style={{
        background:
          "linear-gradient(135deg, #5e6ad2 0%, #7170ff 100%)",
        boxShadow: "0 0 12px rgba(113, 112, 255, 0.35)",
      }}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#f7f8f8"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 2L3 7v5c0 5 3.5 9.5 9 10 5.5-.5 9-5 9-10V7l-9-5z" />
      </svg>
    </div>
  );
}
