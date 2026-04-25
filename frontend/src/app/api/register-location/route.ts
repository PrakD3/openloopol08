// POST /api/register-location
// Receives GPS + phone from NotificationOptIn component
// Proxies to Python backend /register-location endpoint

import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { phone, lat, lon } = body;

  if (!phone || !lat || !lon) {
    return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
  }

  // Validate E.164 phone format
  if (!/^\+[1-9]\d{6,14}$/.test(phone)) {
    return NextResponse.json({ error: 'Invalid phone format. Use E.164 e.g. +971501234567' }, { status: 400 });
  }

  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const res = await fetch(`${backendUrl}/register-location`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: crypto.randomUUID(),
        phone,
        lat,
        lon,
      }),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  }
}
