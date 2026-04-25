'use client';

/**
 * NotificationOptIn
 * Asks user for GPS location + phone number to register for proximity alerts.
 * Posts to /api/register-location which proxies to Python backend.
 * Uses BoldKit components only.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from 'react-i18next';

type RegistrationState = 'idle' | 'requesting-gps' | 'entering-phone' | 'submitting' | 'done' | 'error';

export function NotificationOptIn() {
  const { t } = useTranslation();
  const [state, setState] = useState<RegistrationState>('idle');
  const [phone, setPhone] = useState('');
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [error, setError] = useState('');

  const requestGPS = () => {
    setState('requesting-gps');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setState('entering-phone');
      },
      (err) => {
        setError(`GPS error: ${err.message}`);
        setState('error');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const submitRegistration = async () => {
    if (!coords || !phone) return;
    setState('submitting');
    try {
      const res = await fetch('/api/register-location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone,
          lat: coords.lat,
          lon: coords.lon,
        }),
      });
      if (res.ok) {
        setState('done');
      } else {
        setError('Registration failed. Check your phone number format.');
        setState('error');
      }
    } catch {
      setError('Network error. Please try again.');
      setState('error');
    }
  };

  if (state === 'done') {
    return (
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="pt-4">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-primary border-primary">✓ Alerts Active</Badge>
            <span className="text-sm text-muted-foreground">
              You will receive SMS alerts for verified disasters within 10km.
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">📡 Get Nearby Alerts</span>
          <Badge variant="secondary">Free</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Receive SMS when a verified real disaster is detected within 10km of you.
          Alerts only fire for confirmed events — never for AI-generated or misleading content.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {state === 'idle' && (
          <Button onClick={requestGPS} className="w-full">
            Enable Location & Get Alerts
          </Button>
        )}
        {state === 'requesting-gps' && (
          <p className="text-sm text-muted-foreground animate-pulse">
            Requesting GPS permission...
          </p>
        )}
        {state === 'entering-phone' && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              📍 Location captured. Enter your phone number (E.164 format, e.g. +971501234567):
            </p>
            <Input
              type="tel"
              placeholder="+971501234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <Button onClick={submitRegistration} disabled={!phone} className="w-full">
              Register for Alerts
            </Button>
          </div>
        )}
        {state === 'submitting' && (
          <p className="text-sm text-muted-foreground animate-pulse">Registering...</p>
        )}
        {state === 'error' && (
          <div className="space-y-2">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" onClick={() => setState('idle')}>Try Again</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
