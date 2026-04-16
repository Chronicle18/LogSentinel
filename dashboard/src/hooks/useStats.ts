import { useEffect, useRef, useState } from "react";
import { fetchStats } from "../lib/api";
import type { StatsResponse } from "../lib/types";

const POLL_MS = 5000;

export function useStats(): {
  data: StatsResponse | null;
  loading: boolean;
  error: string | null;
} {
  const [data, setData] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    let timer: ReturnType<typeof setInterval>;

    const load = async () => {
      try {
        const res = await fetchStats();
        if (!mounted.current) return;
        setData(res);
        setError(null);
      } catch (e) {
        if (!mounted.current) return;
        setError(e instanceof Error ? e.message : "Failed to load stats");
      } finally {
        if (mounted.current) setLoading(false);
      }
    };

    load();
    timer = setInterval(load, POLL_MS);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, []);

  return { data, loading, error };
}
