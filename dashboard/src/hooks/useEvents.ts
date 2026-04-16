import { useEffect, useRef, useState } from "react";
import { fetchEvents } from "../lib/api";
import type { EventListResponse, EventsQueryParams } from "../lib/types";

const POLL_MS = 5000;

export function useEvents(params: EventsQueryParams = {}): {
  data: EventListResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
} {
  const [data, setData] = useState<EventListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const paramKey = JSON.stringify(params);

  const load = async (p: EventsQueryParams) => {
    try {
      const res = await fetchEvents(p);
      if (!mounted.current) return;
      setData(res);
      setError(null);
    } catch (e) {
      if (!mounted.current) return;
      setError(e instanceof Error ? e.message : "Failed to load events");
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  useEffect(() => {
    mounted.current = true;
    const parsed = JSON.parse(paramKey) as EventsQueryParams;
    load(parsed);
    const timer = setInterval(() => load(parsed), POLL_MS);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [paramKey]);

  return {
    data,
    loading,
    error,
    refresh: () => load(JSON.parse(paramKey) as EventsQueryParams),
  };
}
