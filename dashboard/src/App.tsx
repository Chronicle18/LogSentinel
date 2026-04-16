import { useEffect, useState } from "react";
import { Header } from "./components/ui/Header";
import { StatTile } from "./components/ui/StatTile";
import { LogVolumeChart } from "./components/panels/LogVolumeChart";
import { ErrorRatePanel } from "./components/panels/ErrorRatePanel";
import { SeverityChart } from "./components/panels/SeverityChart";
import { JobTracker } from "./components/panels/JobTracker";
import { EventTable } from "./components/panels/EventTable";
import { MitreHeatmap } from "./components/panels/MitreHeatmap";
import { ValidatorPanel } from "./components/panels/ValidatorPanel";
import { useStats } from "./hooks/useStats";
import { fetchSourcetypes } from "./lib/api";
import type { SourcetypeInfo } from "./lib/types";

function App() {
  const { data: stats, error: statsError } = useStats();
  const [sourcetypes, setSourcetypes] = useState<SourcetypeInfo[]>([]);
  const [apiStatus, setApiStatus] = useState<
    "connected" | "disconnected" | "checking"
  >("checking");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const res = await fetchSourcetypes();
        if (!active) return;
        setSourcetypes(res.sourcetypes);
      } catch {
        /* handled by per-panel errors */
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (statsError) setApiStatus("disconnected");
    else if (stats) setApiStatus("connected");
  }, [stats, statsError]);

  const totalEvents = stats?.total_events ?? 0;
  const errorRate = stats?.error_rate ?? 0;
  const activeSourcetypes = stats?.by_sourcetype.length ?? 0;
  const distinctTactics = new Set(
    (stats?.by_mitre_tactic ?? [])
      .flatMap((m) => m.tactic.split(","))
      .map((t) => t.trim())
      .filter(Boolean),
  ).size;

  return (
    <div className="min-h-screen bg-bg-canvas text-fg-primary">
      <Header apiStatus={apiStatus} />

      <main className="max-w-[1440px] mx-auto px-6 py-6 flex flex-col gap-6">
        <section className="flex items-baseline justify-between">
          <div>
            <h1
              className="text-h1 font-semibold tracking-tight text-fg-primary"
              style={{ fontFeatureSettings: '"cv01", "ss03"' }}
            >
              Security Overview
            </h1>
            <p className="text-caption text-fg-tertiary mt-1">
              Normalized log telemetry · CIM fields · MITRE ATT&CK tagging
            </p>
          </div>
        </section>

        <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile
            label="Total events"
            value={totalEvents.toLocaleString()}
            sublabel="across all sourcetypes"
          />
          <StatTile
            label="Parse error rate"
            value={`${errorRate.toFixed(2)}%`}
            accent={errorRate >= 5 ? "danger" : "success"}
            sublabel={`${(stats?.total_parse_errors ?? 0).toLocaleString()} errors`}
          />
          <StatTile
            label="Active sourcetypes"
            value={activeSourcetypes}
            sublabel={`of ${sourcetypes.length} configured`}
            accent="brand"
          />
          <StatTile
            label="MITRE tactics"
            value={distinctTactics}
            sublabel="detected in window"
            accent="warning"
          />
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <LogVolumeChart sourcetypes={sourcetypes} />
          </div>
          <div className="flex flex-col gap-6">
            <ErrorRatePanel stats={stats} />
            <SeverityChart stats={stats} />
          </div>
        </section>

        <section>
          <MitreHeatmap stats={stats} />
        </section>

        <section>
          <JobTracker />
        </section>

        <section>
          <EventTable sourcetypes={sourcetypes} />
        </section>

        <section>
          <ValidatorPanel sourcetypes={sourcetypes} />
        </section>

        <footer className="pt-4 pb-8 text-center text-tiny text-fg-quaternary">
          LogSentinel v1.0 · PostgreSQL + FastAPI · polling live · a project by Pranav
        </footer>
      </main>
    </div>
  );
}

export default App;
