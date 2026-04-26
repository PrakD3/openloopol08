'use client';

import type { SOSRegion } from '@/types';
import { useEffect, useRef } from 'react';

interface SOSMapProps {
  sosRegion: SOSRegion;
}

const DISASTER_LABELS: Record<string, string> = {
  flood: '🌊 Flood Zone',
  earthquake: '🏚️ Earthquake Zone',
  cyclone: '🌀 Cyclone Impact Zone',
  tsunami: '🌊 Tsunami Risk Zone',
  wildfire: '🔥 Wildfire Zone',
  landslide: '⛰️ Landslide Zone',
  unknown: '⚠️ Disaster Zone',
};

export function SOSMap({ sosRegion }: SOSMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    if (typeof window === 'undefined') return;

    // Dynamically import leaflet to avoid SSR issues
    Promise.all([
      import('leaflet'),
      // Load CSS
      new Promise<void>((resolve) => {
        if (document.querySelector('link[href*="leaflet"]')) {
          resolve();
          return;
        }
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        link.onload = () => resolve();
        document.head.appendChild(link);
      }),
    ]).then(([L]) => {
      if (!mapRef.current || mapInstanceRef.current) return;

      // Fix default icon paths broken by webpack
      // @ts-expect-error leaflet internals
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });

      const map = L.map(mapRef.current, {
        center: [sosRegion.lat, sosRegion.lng],
        zoom: _zoomForRadius(sosRegion.radiusKm),
        zoomControl: true,
        scrollWheelZoom: false,
        attributionControl: true,
      });

      // OpenStreetMap tile layer — no API key required
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map);

      // Impact radius circle
      const circle = L.circle([sosRegion.lat, sosRegion.lng], {
        radius: sosRegion.radiusKm * 1000, // convert km → metres
        color: sosRegion.color,
        fillColor: sosRegion.color,
        fillOpacity: 0.15,
        weight: 2,
        dashArray: '6 4',
      }).addTo(map);

      // Centre marker with SOS popup
      const label = DISASTER_LABELS[sosRegion.disasterType] ?? '⚠️ Disaster Zone';
      L.marker([sosRegion.lat, sosRegion.lng])
        .addTo(map)
        .bindPopup(
          `<div style="font-family:sans-serif;font-size:13px;line-height:1.5">
            <strong style="color:${sosRegion.color}">${label}</strong><br/>
            <span>${sosRegion.centerName}</span><br/>
            <strong>Impact radius: ${sosRegion.radiusKm} km</strong><br/>
            <em style="color:#ef4444">⚠️ SOS Active — Panic Index ${sosRegion.panicIndex}/10</em>
          </div>`,
          { maxWidth: 240 }
        )
        .openPopup();

      mapInstanceRef.current = map;
    });

    return () => {
      if (mapInstanceRef.current) {
        (mapInstanceRef.current as { remove: () => void }).remove();
        mapInstanceRef.current = null;
      }
    };
  }, [sosRegion]);

  const label = DISASTER_LABELS[sosRegion.disasterType] ?? '⚠️ Disaster Zone';

  return (
    <div className="space-y-3">
      {/* SOS Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full animate-pulse"
            style={{ backgroundColor: sosRegion.color }}
          />
          <p className="text-sm font-semibold text-destructive uppercase tracking-wide">
            🆘 SOS Region Active
          </p>
        </div>
        <span className="text-xs text-muted-foreground">Radius: {sosRegion.radiusKm} km</span>
      </div>

      <p className="text-xs text-muted-foreground">
        {label} centred on <strong>{sosRegion.centerName}</strong>. Impact radius estimated at{' '}
        <strong>{sosRegion.radiusKm} km</strong> based on disaster intensity (panic index{' '}
        {sosRegion.panicIndex}/10). Data via{' '}
        <a
          href="https://www.openstreetmap.org"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-foreground"
        >
          OpenStreetMap
        </a>
        .
      </p>

      {/* Map container */}
      <div
        ref={mapRef}
        className="h-64 w-full rounded-lg overflow-hidden border border-border z-0"
        style={{ isolation: 'isolate' }}
        aria-label={`Map showing ${label} around ${sosRegion.centerName}`}
        id="sos-map"
      />
    </div>
  );
}

function _zoomForRadius(km: number): number {
  if (km <= 10) return 11;
  if (km <= 30) return 10;
  if (km <= 80) return 9;
  if (km <= 200) return 8;
  return 7;
}
