import { useEffect, useRef, useState } from "react";
import { fetchJob } from "../lib/api";
import type { JobResponse } from "../lib/types";

// Per PRD: job tracker polls every 2s for fast progress updates.
const POLL_MS = 2000;

export function useJobStatus(jobId: string | null): {
  data: JobResponse | null;
  loading: boolean;
  error: string | null;
} {
  const [data, setData] = useState<JobResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    if (!jobId) {
      setData(null);
      return;
    }
    setLoading(true);
    let timer: ReturnType<typeof setInterval>;

    const load = async () => {
      try {
        const res = await fetchJob(jobId);
        if (!mounted.current) return;
        setData(res);
        setError(null);
        // Stop polling once job reaches terminal state
        if (res.status === "complete" || res.status === "failed") {
          clearInterval(timer);
        }
      } catch (e) {
        if (!mounted.current) return;
        setError(e instanceof Error ? e.message : "Failed to load job");
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
  }, [jobId]);

  return { data, loading, error };
}
