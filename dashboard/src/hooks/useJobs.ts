import { useEffect, useRef, useState } from "react";
import { fetchJobs } from "../lib/api";
import type { JobResponse } from "../lib/types";

// Per PRD: JobTracker polls every 2s to surface active job progress quickly.
const POLL_MS = 2000;

export function useJobs(limit = 10): {
  data: JobResponse[] | null;
  loading: boolean;
  error: string | null;
} {
  const [data, setData] = useState<JobResponse[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const load = async () => {
      try {
        const res = await fetchJobs(limit);
        if (!mounted.current) return;
        setData(res);
        setError(null);
      } catch (e) {
        if (!mounted.current) return;
        setError(e instanceof Error ? e.message : "Failed to load jobs");
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
  }, [limit]);

  return { data, loading, error };
}
