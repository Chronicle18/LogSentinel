import { useEffect, useRef, useState } from "react";
import { fetchTimeseries } from "../lib/api";
import type { TimeseriesResponse } from "../lib/types";

const POLL_MS = 5000;

export function useTimeseries(params: {
  bucket_minutes?: number;
  window_hours?: number;
  sourcetype?: string;
}): { data: TimeseriesResponse | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<TimeseriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const key = JSON.stringify(params);

  useEffect(() => {
    mounted.current = true;
    const parsed = JSON.parse(key);
    const load = async () => {
      try {
        const res = await fetchTimeseries(parsed);
        if (!mounted.current) return;
        setData(res);
        setError(null);
      } catch (e) {
        if (!mounted.current) return;
        setError(
          e instanceof Error ? e.message : "Failed to load timeseries",
        );
      } finally {
        if (mounted.current) setLoading(false);
      }
    };
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [key]);

  return { data, loading, error };
}
