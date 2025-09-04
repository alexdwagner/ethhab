import { NextResponse } from 'next/server';
import { getBackendBaseUrl } from '@/lib/env';

export async function GET(request: Request) {
  const backend = getBackendBaseUrl();
  const url = new URL('/debug', backend);
  const headers: Record<string, string> = {};
  const auth = request.headers.get('authorization');
  if (auth) headers['authorization'] = auth;
  try {
    const res = await fetch(url.toString(), { cache: 'no-store', headers });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (e: any) {
    return NextResponse.json({ error: String(e) }, { status: 502 });
  }
}

