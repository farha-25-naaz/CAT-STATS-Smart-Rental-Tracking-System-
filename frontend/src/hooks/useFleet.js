import { useCallback, useEffect, useRef, useState } from 'react';
import { getLiveAssets, getSites } from '../api/endpoints';
import { normalizeFleet } from '../api/normalize';

// Loads the fleet from the backend once, then keeps it fresh:
//  - while `polling` is true, re-fetches every `intervalMs`
//  - the live WebSocket (useLiveSocket) patches individual assets in between
export function useFleet({ polling = true, intervalMs = 8000 } = {}) {
  const [assets, setAssets] = useState([]);
  const [sites, setSites] = useState([]);
  const [status, setStatus] = useState('loading'); // loading | ready | error
  const [error, setError] = useState(null);
  const sitesRef = useRef([]);
  const mountedRef = useRef(true);

  const load = useCallback(async (signal) => {
    try {
      if (!sitesRef.current.length) {
        sitesRef.current = await getSites({ signal }).catch(() => []);
        if (mountedRef.current) setSites(sitesRef.current);
      }
      const raw = await getLiveAssets({ signal });
      if (!mountedRef.current) return;
      setAssets(normalizeFleet(raw, sitesRef.current));
      setStatus('ready');
      setError(null);
    } catch (err) {
      if (err.name === 'AbortError' || !mountedRef.current) return;
      setStatus((s) => (s === 'ready' ? 'ready' : 'error'));
      setError(err);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const ctrl = new AbortController();
    load(ctrl.signal);
    return () => {
      mountedRef.current = false;
      ctrl.abort();
    };
  }, [load]);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(() => load(), intervalMs);
    return () => clearInterval(id);
  }, [polling, intervalMs, load]);

  return { assets, setAssets, sites, status, error, refetch: () => load() };
}
