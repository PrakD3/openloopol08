'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import 'leaflet/dist/leaflet.css';

// Leaflet requires window, so we must use a dynamic import with no SSR
const MapContainer = dynamic(() => import('react-leaflet').then((mod) => mod.MapContainer), {
  ssr: false,
});
const TileLayer = dynamic(() => import('react-leaflet').then((mod) => mod.TileLayer), {
  ssr: false,
});
const Marker = dynamic(() => import('react-leaflet').then((mod) => mod.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then((mod) => mod.Popup), { ssr: false });

interface LocationMapProps {
  latitude: number | null;
  longitude: number | null;
  label: string;
}

export function LocationMap({ latitude, longitude, label }: LocationMapProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);

    // Fix for Leaflet default icon paths in Next.js
    if (typeof window !== 'undefined') {
      const L = require('leaflet');
      L.Icon.Default.prototype._getIconUrl = undefined;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });
    }
  }, []);

  if (!isMounted || latitude === null || longitude === null) {
    return null;
  }

  const center: [number, number] = [latitude, longitude];

  return (
    <div className="w-full h-[300px] border-4 border-foreground bk-shadow-sm overflow-hidden relative z-0">
      <MapContainer center={center} zoom={13} scrollWheelZoom={false} className="w-full h-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={center}>
          <Popup>
            <span className="font-black uppercase tracking-widest text-xs">{label}</span>
          </Popup>
        </Marker>
      </MapContainer>
      <div className="absolute top-2 right-2 z-[1000] bg-primary text-primary-foreground text-[10px] font-black uppercase tracking-widest px-2 py-1 border-2 border-foreground bk-shadow-sm">
        GPS: {latitude.toFixed(4)}, {longitude.toFixed(4)}
      </div>
    </div>
  );
}
