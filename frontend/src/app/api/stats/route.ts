import { NextResponse } from 'next/server';
import { getBackendBaseUrl } from '@/lib/env';

export async function GET() {
  const backend = getBackendBaseUrl();
  const url = new URL('/api/stats', backend);
  try {
    const res = await fetch(url.toString(), { cache: 'no-store' });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json({ error: String(e) }, { status: 502 });
  }
}

