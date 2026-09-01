import React, { useEffect, useRef, useState } from 'react';
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode';

// Camera QR reader. Calls onDecode(text) once on the first successful read.
//
// The start is deferred behind a short timer: React StrictMode mounts the
// component twice, and the throwaway first mount is unmounted before the timer
// fires, so the camera is only ever acquired once.
export default function QrScanner({ onDecode, onError }) {
  const hostRef = useRef(null);
  const onDecodeRef = useRef(onDecode);
  const onErrorRef = useRef(onError);
  onDecodeRef.current = onDecode;
  onErrorRef.current = onError;

  const [status, setStatus] = useState('starting'); // starting | live | failed
  const [failMsg, setFailMsg] = useState('');

  useEffect(() => {
    let scanner = null;
    let done = false;
    let cancelled = false;

    const timer = setTimeout(async () => {
      const host = hostRef.current;
      if (!host || cancelled) return;

      scanner = new Html5Qrcode(host.id, {
        verbose: false,
        // Only look for QR codes -> fewer decode passes per frame.
        formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
        // Use the browser's native BarcodeDetector when available: much faster
        // and far more tolerant of glare / angle / small codes than the JS decoder.
        experimentalFeatures: { useBarCodeDetectorIfSupported: true },
      });
      try {
        await scanner.start(
          {
            facingMode: 'environment',
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          {
            fps: 20,
            // Scan box tracks the viewfinder size so it's easy to line up.
            qrbox: (vw, vh) => {
              const m = Math.max(200, Math.floor(Math.min(vw, vh) * 0.75));
              return { width: m, height: m };
            },
          },
          (text) => {
            if (done) return;
            done = true;
            scanner.stop().catch(() => {}).finally(() => onDecodeRef.current?.(text.trim()));
          },
          () => {},
        );
        if (!cancelled) setStatus('live');
      } catch (err) {
        if (cancelled) return;
        setStatus('failed');
        setFailMsg(err?.message || String(err));
        onErrorRef.current?.(err);
      }
    }, 150);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      const s = scanner;
      if (s) {
        const stop = s.isScanning ? s.stop() : Promise.resolve();
        stop.catch(() => {}).finally(() => {
          try { s.clear(); } catch { /* torn down */ }
        });
      }
    };
  }, []);

  const hostId = useRef(`qr-host-${Math.random().toString(36).slice(2)}`).current;

  return (
    <div className="relative w-full min-h-[300px] overflow-hidden rounded-xl border border-[#333] bg-black">
      <div id={hostId} ref={hostRef} className="w-full [&_video]:w-full [&_video]:block" />
      {status !== 'live' && (
        <div className="absolute inset-0 flex items-center justify-center text-center px-3 text-[11px] text-neutral-400">
          {status === 'failed' ? `Camera unavailable: ${failMsg}` : 'Starting camera…'}
        </div>
      )}
    </div>
  );
}
