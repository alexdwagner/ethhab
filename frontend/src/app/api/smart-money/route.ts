import { NextResponse } from 'next/server';
import { getBackendBaseUrl } from '@/lib/env';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const backend = getBackendBaseUrl();
  const url = new URL('/smart-money', backend);
  searchParams.forEach((v, k) => url.searchParams.set(k, v));

  try {
    const res = await fetch(url.toString(), { cache: 'no-store' });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json({ error: String(e) }, { status: 502 });
  }
}

