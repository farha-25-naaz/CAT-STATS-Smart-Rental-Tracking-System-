import { useEffect, useRef, useState } from 'react';
import { WS_URL } from '../api/client';
import { applyTelemetryFrame } from '../api/normalize';

// Opens the /ws/live WebSocket and patches the fleet in place as frames arrive.
// Reconnects with capped exponential backoff while `enabled` is true.
export function useLiveSocket({ enabled = true, setAssets, onLockout, onLockoutCleared, onEvent } = {}) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!enabled) return undefined;
    let closedByUs = false;

    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setConnected(true);
      };

      ws.onmessage = (evt) => {
        let msg;
        try {
          msg = JSON.parse(evt.data);
        } catch {
          return;
        }
        const event = msg.event;
        onEvent?.(msg);

        if (event === 'TELEMETRY' && msg.asset_id) {
          setAssets?.((prev) =>
            prev.map((a) => (a.id === msg.asset_id ? applyTelemetryFrame(a, msg) : a)),
          );
        } else if (event === 'SAFETY_LOCKOUT' && msg.asset_id) {
          setAssets?.((prev) =>
            prev.map((a) =>
              a.id === msg.asset_id
                ? { ...a, status: 'CRITICAL_ALERT', rawStatus: 'SAFETY_LOCKOUT', isAnomaly: true, anomaly: msg.reason || a.anomaly || 'Safety lockout' }
                : a,
            ),
          );
          onLockout?.(msg);
        } else if (event === 'LOCKOUT_CLEARED' && msg.asset_id) {
          setAssets?.((prev) =>
            prev.map((a) =>
              a.id === msg.asset_id
                ? { ...a, status: 'ACTIVE', rawStatus: 'ACTIVE', isAnomaly: false, anomaly: null }
                : a,
            ),
          );
          onLockoutCleared?.(msg);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (closedByUs) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
        retryRef.current += 1;
        timerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      closedByUs = true;
      clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [enabled, setAssets, onLockout, onLockoutCleared, onEvent]);

  return { connected };
}
