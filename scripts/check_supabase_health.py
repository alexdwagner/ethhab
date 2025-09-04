#!/usr/bin/env python3
"""
Supabase Health Check
- Verifies connection, read access, and write permissions (with cleanup)
- Safe to run repeatedly; writes a transient row to dex_interactions
"""

import sys
import time
from datetime import datetime

sys.path.insert(0, '.')

from config import config
from src.data.supabase_client import supabase_client


def main() -> int:
    print("🔗 Supabase Health Check")
    print("=" * 40)

    # Basic config check
    missing = []
    if not config.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not (config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_ANON_KEY):
        missing.append("SUPABASE_(SERVICE_ROLE_KEY|ANON_KEY)")
    if missing:
        print(f"❌ Missing env: {', '.join(missing)}")
        return 1

    # Client check
    if not supabase_client:
        print("❌ Supabase client failed to initialize")
        return 1

    client = supabase_client.get_client()

    # Read test
    try:
        res = client.table('dex_routers').select('*').limit(1).execute()
        print("✅ Read access: dex_routers selectable")
    except Exception as e:
        print(f"❌ Read failed on dex_routers: {e}")
        return 1

    # Write test (transient row into dex_interactions)
    test_tx = f"healthcheck-{int(time.time())}"
    test_row = {
        'address': '0x0000000000000000000000000000000000000001',
        'router_address': '0x0000000000000000000000000000000000000002',
        'tx_hash': test_tx,
        'block_number': 0,
        'timestamp': datetime.utcnow().isoformat(),
        'gas_spent_eth': 0,
    }

    wrote = False
    try:
        client.table('dex_interactions').insert(test_row).execute()
        wrote = True
        print("✅ Write access: inserted into dex_interactions")
    except Exception as e:
        print(f"⚠️  Write failed on dex_interactions: {e}")
        print("   If using anon key, add RLS policies or set SUPABASE_SERVICE_ROLE_KEY for backend.")

    # Cleanup
    if wrote:
        try:
            client.table('dex_interactions').delete().eq('tx_hash', test_tx).execute()
            print("🧹 Cleanup: removed test row")
        except Exception as e:
            print(f"⚠️  Cleanup failed: {e}")

    # Summary
    ok = wrote
    if ok:
        print("\n✅ Supabase health OK: read/write verified")
        return 0
    else:
        print("\n⚠️  Supabase connectivity OK, but writes failed. Configure service-role key or RLS policies.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

