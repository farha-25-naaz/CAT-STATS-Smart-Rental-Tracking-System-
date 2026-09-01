import { useState, useEffect } from 'react';
import { initialAssets } from '../data/mockAssets';

export function useTelemetryStream(isLiveStreaming = true) {
  const [assets, setAssets] = useState(initialAssets);

  useEffect(() => {
    if (!isLiveStreaming) return;

    const interval = setInterval(() => {
      setAssets((prevAssets) =>
        prevAssets.map((asset) => {
          // Stationary idle machines stay in place
          if (asset.speedKmH === 0 && asset.status === 'IDLE_WARNING') {
            return {
              ...asset,
              idleHours: parseFloat(((asset.idleHours || 0) + 0.01).toFixed(2)),
            };
          }

          // Move the active machines along a visible local path (~10-25 meters per tick)
          const angle = (Date.now() / 1500) + (asset.id === 'EQX1001' ? 0 : 2);
          const stepSize = 0.00035; // Noticeable movement at site zoom level
          const deltaLat = Math.sin(angle) * stepSize;
          const deltaLng = Math.cos(angle) * stepSize;

          const newLat = parseFloat((asset.coords[0] + deltaLat).toFixed(6));
          const newLng = parseFloat((asset.coords[1] + deltaLng).toFixed(6));
          const newCoords = [newLat, newLng];

          const updatedTrail = [...(asset.trail || []), newCoords].slice(-12);

          return {
            ...asset,
            coords: newCoords,
            trail: updatedTrail,
            engineHours: parseFloat(((asset.engineHours || 0) + 0.01).toFixed(2)),
            fuelLevel: Math.max(15, parseFloat(((asset.fuelLevel || 80) - 0.02).toFixed(1))),
            speedKmH: Math.round(6 + Math.abs(Math.sin(angle)) * 8),
            tiltAngle: parseFloat((3.0 + Math.sin(angle) * 1.5).toFixed(1)),
          };
        })
      );
    }, 1800); // Smooth update every 1.8 seconds

    return () => clearInterval(interval);
  }, [isLiveStreaming]);

  return { assets, setAssets };
}