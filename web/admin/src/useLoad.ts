import { useCallback, useEffect, useState } from "react";

export function useLoad<T>(fetcher: () => Promise<T>, refreshMs?: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(() => {
    fetcher().then((d) => { setData(d); setError(null); },
                   (e) => setError((e as Error).message));
  }, [fetcher]);
  useEffect(() => {
    reload();
    if (!refreshMs) return;
    const timer = setInterval(reload, refreshMs);
    return () => clearInterval(timer);
  }, [reload, refreshMs]);
  return { data, error, reload };
}
