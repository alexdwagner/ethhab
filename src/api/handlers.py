#!/usr/bin/env python3
"""
API Handlers
HTTP request handlers for whale tracker
"""

import json
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from src.services.whale_service import WhaleService
from src.services.roi_service import ROIService
from src.services.whale_scanner_service import whale_scanner_service
from src.data.whale_repository import whale_repository
from src.data.smart_money_repository import smart_money_repository
from src.data.supabase_client import supabase_client
from src.services.pricing_service import pricing_service
from src.services.metrics_service import metrics_service
from src.services.smart_money_discovery import smart_money_discovery
import os

class WhaleAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for whale API"""
    
    # Cooldown for protected write health check (seconds)
    _write_health_cooldown = 60
    _last_db_write_check_ts = 0.0
    _debug_cooldown = 30
    _last_debug_check_ts = 0.0
    
    def __init__(self, *args, **kwargs):
        # Initialize services
        self.whale_service = WhaleService()
        self.roi_service = ROIService()
        
        # Supabase-only architecture
        if not whale_repository:
            raise ValueError(
                "Supabase not configured. Please:\n"
                "1. Set SUPABASE_URL and key (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY) in .env\n"
                "2. Run: python3 scripts/setup_supabase.py"
            )
        
        self.db = whale_repository
        
        # Cache
        self.whale_cache = {}
        self.cache_timestamp = None
        self.cache_duration = 300  # 5 minutes
        
        # Request timing for monitoring
        self.request_start_time = None
        
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests with timing middleware"""
        # Start timing
        self.request_start_time = time.time()
        
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path == '/' or path == '/index.html':
                self.serve_dashboard()
            elif path == '/api/whales':
                self.serve_whales()
            elif path == '/api/stats':
                self.serve_stats()
            elif path == '/api/scan/trigger' and self.check_dev_auth():
                self.serve_scan_trigger()
            elif path == '/api/scan/status':
                self.serve_scan_status()
            elif path == '/health':
                self.serve_health()
            elif path == '/health/db-write' and self.check_dev_auth():
                self.serve_health_db_write()
            elif path == '/smart-money':
                self.serve_smart_money()
            elif path == '/smart-money/stats':
                self.serve_smart_money_stats()
            elif path == '/admin/db-stats':
                self.serve_admin_db_stats()
            elif path == '/debug':
                self.serve_debug()
            else:
                self.send_error(404, "Not Found")
        finally:
            # Log request timing
            self.log_request_timing(path)

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path == '/admin/refresh':
            self.serve_admin_refresh()
        else:
            self.send_error(404, "Not Found")
    
    def serve_dashboard(self):
        """Redirect to NextJS frontend"""
        self.send_response(302)
        self.send_header('Location', 'http://localhost:3000')
        self.end_headers()
    
    def serve_whales(self):
        """Serve whale data with ROI scores"""
        self.send_json_response(self.get_whale_data())
    
    def serve_stats(self):
        """Serve database statistics"""
        stats = self.db.get_stats()
        self.send_json_response(stats)

    def serve_smart_money(self):
        """Serve Smart Money data.
        - Default: fallback aggregation across candidates + activity
        - If query `watchlist=1`, return only qualified watchlist entries (optionally gated by `min_sharpe`)
        """
        if not smart_money_repository:
            self.send_json_response({'error': 'Smart money repository not available'}, status=503)
            return
        
        # Parse basic query params
        from urllib.parse import parse_qs, urlparse
        qs = parse_qs(urlparse(self.path).query)
        try:
            limit = int(qs.get('limit', ['50'])[0])
            min_swaps = int(qs.get('min_swaps', ['10'])[0])
            active_days = int(qs.get('active_days', ['30'])[0])
        except ValueError:
            limit, min_swaps, active_days = 50, 10, 30

        watchlist_only = (qs.get('watchlist', ['0'])[0]).lower() in ('1', 'true', 'yes')
        min_sharpe = None
        try:
            if 'min_sharpe' in qs:
                min_sharpe = float(qs.get('min_sharpe', ['1.0'])[0])
        except ValueError:
            min_sharpe = None
        # Sorting parameters
        sort = (qs.get('sort', ['auto'])[0]).lower()  # auto|sharpe|pnl|win_rate|activity|last_activity
        priced_only = (qs.get('priced_only', ['0'])[0]).lower() in ('1', 'true', 'yes')
        min_coverage = None
        min_priced_trades = None
        try:
            if 'min_coverage' in qs:
                min_coverage = float(qs.get('min_coverage', ['60'])[0])
        except ValueError:
            min_coverage = None
        try:
            if 'min_priced_trades' in qs:
                min_priced_trades = int(qs.get('min_priced_trades', ['10'])[0])
        except ValueError:
            min_priced_trades = None
        
        meta = {'sort': sort, 'fallback_sort': False}
        if watchlist_only:
            ms = 1.0 if min_sharpe is None else min_sharpe
            data, meta['fallback_sort'] = smart_money_repository.get_watchlist_sorted(
                limit=limit,
                min_sharpe=ms,
                sort=sort,
                priced_only=priced_only,
                min_coverage=min_coverage,
                min_priced_trades=min_priced_trades
            )
        else:
            data, meta['fallback_sort'] = smart_money_repository.get_smart_money_leaderboard(
                limit=limit,
                min_dex_swaps=min_swaps,
                active_within_days=active_days,
                sort=sort,
                priced_only=priced_only,
                min_coverage=min_coverage,
                min_priced_trades=min_priced_trades
            )
        self.send_json_response({'items': data, 'count': len(data), 'limit': limit, **meta})
    
    def serve_health(self):
        """Health check endpoint for monitoring and debugging"""
        import os
        start_time = time.time()
        try:
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            
            # Check database connection
            try:
                stats = self.db.get_stats()
                whale_count = stats.get('total_whales', 0)
                health_data.update({
                    'database': 'connected',
                    'whale_count': whale_count,
                    'whales_with_roi': stats.get('whales_with_roi', 0)
                })
                
                # Check data freshness (if we have whales)
                if whale_count > 0:
                    # For now, we'll assume data is fresh since we just implemented database-first
                    # In D-016, we'll add actual last_updated tracking
                    health_data['last_updated'] = 'recent'  
                else:
                    health_data['status'] = 'degraded'
                    health_data['warning'] = 'No whale data found'
                    
            except Exception as db_error:
                health_data.update({
                    'status': 'unhealthy',
                    'database': 'failed',
                    'database_error': str(db_error)
                })
            
            # Basic system metrics (without psutil dependency)
            try:
                health_data['process_id'] = os.getpid()
            except Exception:
                pass
            
            # Response time
            response_time = (time.time() - start_time) * 1000
            health_data['response_time_ms'] = round(response_time, 1)
            
            # Determine overall health status
            if response_time > 1000:  # > 1 second is degraded
                health_data['status'] = 'degraded'
                health_data['warning'] = 'Slow response time'
            
            # Return appropriate HTTP status
            status_code = 200
            if health_data['status'] == 'unhealthy':
                status_code = 503  # Service Unavailable
            elif health_data['status'] == 'degraded':
                status_code = 200  # Still OK, just warning
            
            self.send_json_response(health_data, status=status_code)
        except Exception as e:
            error_response = {
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'response_time_ms': round((time.time() - start_time) * 1000, 1)
            }
            self.send_json_response(error_response, status=503)

    def serve_debug(self):
        """Protected verbose diagnostics for developers (D-025)."""
        # Auth: require dev token
        auth = self.headers.get('Authorization', '')
        dev_token = os.getenv('DEV_DEBUG_TOKEN', '')
        dev_debug = os.getenv('DEV_DEBUG', '0') in ('1', 'true', 'True', 'yes', 'on')
        token_ok = dev_token and auth.startswith('Bearer ') and auth.split(' ', 1)[1].strip() == dev_token
        if not (dev_debug or token_ok):
            self.send_json_response({'error': 'Forbidden'}, status=403)
            return

        # Cooldown
        now_ts = time.time()
        if now_ts - self._last_debug_check_ts < self._debug_cooldown:
            self.send_json_response({'error': 'Too Many Requests', 'retry_after_sec': int(self._debug_cooldown - (now_ts - self._last_debug_check_ts))}, status=429)
            return
        self._last_debug_check_ts = now_ts

        def mask(val: str) -> str:
            if not val:
                return ''
            s = str(val)
            if len(s) <= 8:
                return '****'
            return s[:4] + '...' + s[-4:]

        payload = {
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'process_id': os.getpid(),
            'env': {
                'SUPABASE_URL_present': bool(os.getenv('SUPABASE_URL')),
                'ETH_RPC_URL_present': bool(os.getenv('ETH_RPC_URL')),
                'SMART_MONEY_DISABLE_NETWORK': os.getenv('SMART_MONEY_DISABLE_NETWORK', '0'),
                'DEV_DEBUG_TOKEN_masked': mask(dev_token),
            },
            'db': {
                'connected': False,
            },
            'counts': {},
            'coverage': {},
        }

        # DB connectivity + counts
        try:
            client = supabase_client.get_client()
            # priced_trades last 24h
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            pt = client.table('priced_trades').select('id', count='exact').gte('block_ts', cutoff).execute()
            tm = client.table('trader_metrics').select('address', count='exact').execute()
            wl = client.table('smart_money_candidates').select('id', count='exact').eq('qualifies_smart_money', True).execute()
            payload['db']['connected'] = True
            payload['counts'] = {
                'priced_trades_24h': pt.count or 0,
                'trader_metrics_rows': tm.count or 0,
                'watchlist_count': wl.count or 0,
            }
            # Coverage distribution (sample up to 1000 rows)
            cov_res = client.table('smart_money_candidates').select('coverage_pct').limit(1000).execute()
            buckets = {'0': 0, '0-25': 0, '25-50': 0, '50-75': 0, '75-100': 0}
            for r in (cov_res.data or []):
                try:
                    c = float(r.get('coverage_pct') or 0)
                except Exception:
                    c = 0.0
                if c <= 0:
                    buckets['0'] += 1
                elif c < 25:
                    buckets['0-25'] += 1
                elif c < 50:
                    buckets['25-50'] += 1
                elif c < 75:
                    buckets['50-75'] += 1
                else:
                    buckets['75-100'] += 1
            payload['coverage'] = buckets
        except Exception as e:
            payload['db']['error'] = str(e)

        self.send_json_response(payload, status=200)

    def serve_smart_money_stats(self):
        """Return lightweight stats for Smart Money summary (D-023)."""
        if not smart_money_repository:
            self.send_json_response({'error': 'Smart money repository not available'}, status=503)
            return

        try:
            client = supabase_client.get_client()
            # Watchlist count
            wl = client.table('smart_money_candidates').select('id', count='exact').eq('qualifies_smart_money', True).execute()
            watchlist_count = wl.count or 0

            # Recent active in the last 24h from address_activity
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            ra = client.table('address_activity').select('address', count='exact').gte('last_activity_at', cutoff).execute()
            recent_active_24h = ra.count or 0

            # Average swaps among watchlist (use dex_swaps_90d where available)
            wl_rows = client.table('smart_money_candidates').select('dex_swaps_90d').eq('qualifies_smart_money', True).limit(500).execute()
            swaps = [int(r.get('dex_swaps_90d') or 0) for r in (wl_rows.data or [])]
            avg_swaps_90d = round(sum(swaps) / len(swaps), 2) if swaps else 0

            payload = {
                'watchlist_count': watchlist_count,
                'recent_active_24h': recent_active_24h,
                'avg_swaps_90d': avg_swaps_90d,
                'generated_at': datetime.utcnow().isoformat(),
            }
            self.send_json_response(payload)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def serve_admin_db_stats(self):
        """Protected DB stats: qualified counts under gate presets."""
        # Auth
        auth = self.headers.get('Authorization', '')
        admin_token = os.getenv('ADMIN_API_TOKEN', '')
        if not admin_token or not auth.startswith('Bearer ') or auth.split(' ', 1)[1].strip() != admin_token:
            self.send_json_response({'error': 'Forbidden'}, status=403)
            return

        # Params
        from urllib.parse import parse_qs, urlparse
        qs = parse_qs(urlparse(self.path).query)
        def _int(name, default):
            try:
                return int((qs.get(name, [str(default)])[0]))
            except Exception:
                return default
        def _float(name, default):
            try:
                return float((qs.get(name, [str(default)])[0]))
            except Exception:
                return default

        strict_trades = _int('strict_trades', 5)
        strict_cov = _float('strict_cov', 60)
        loose_trades = _int('loose_trades', 3)
        loose_cov = _float('loose_cov', 40)

        try:
            client = supabase_client.get_client()
            # Strict
            s = client.table('smart_money_candidates').select('id', count='exact') \
                .gte('priced_trades_count', strict_trades) \
                .gte('coverage_pct', strict_cov).execute()
            # Loose
            l = client.table('smart_money_candidates').select('id', count='exact') \
                .gte('priced_trades_count', loose_trades) \
                .gte('coverage_pct', loose_cov).execute()
            # Watchlist strict
            ws = client.table('smart_money_candidates').select('id', count='exact') \
                .eq('qualifies_smart_money', True) \
                .gte('priced_trades_count', strict_trades) \
                .gte('coverage_pct', strict_cov).execute()

            self.send_json_response({
                'qualified_strict': s.count or 0,
                'qualified_loose': l.count or 0,
                'watchlist_strict': ws.count or 0,
                'strict_trades': strict_trades,
                'strict_cov': strict_cov,
                'loose_trades': loose_trades,
                'loose_cov': loose_cov,
            })
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def serve_admin_refresh(self):
        """Protected admin endpoint to run the refresh pipeline (D-027)."""
        # Auth
        auth = self.headers.get('Authorization', '')
        admin_token = os.getenv('ADMIN_API_TOKEN', '')
        if not admin_token or not auth.startswith('Bearer ') or auth.split(' ', 1)[1].strip() != admin_token:
            self.send_json_response({'error': 'Forbidden'}, status=403)
            return

        # Preconditions
        if not (smart_money_repository and pricing_service and metrics_service and smart_money_discovery):
            self.send_json_response({'error': 'Services unavailable'}, status=503)
            return

        # Parse body
        length = int(self.headers.get('Content-Length', '0') or 0)
        try:
            raw = self.rfile.read(length) if length else b'{}'
            body = json.loads(raw.decode('utf-8') or '{}')
        except Exception:
            body = {}

        top = int(body.get('top', 100))
        hours = int(body.get('hours', 720))
        price_days = int(body.get('price_days', 90))
        metrics_days = int(body.get('metrics_days', 90))
        activity_days = int(body.get('activity_days', 90))
        time_budget = int(body.get('time_budget', 240))

        # Log start
        client = supabase_client.get_client()
        log_row = {
            'job_name': 'admin_refresh',
            'status': 'running',
            'params': {
                'top': top,
                'hours': hours,
                'price_days': price_days,
                'metrics_days': metrics_days,
                'activity_days': activity_days,
                'time_budget': time_budget,
            }
        }
        try:
            ins = client.table('job_logs').insert(log_row).execute()
            job_id = (ins.data or [{}])[0].get('id')
        except Exception:
            job_id = None

        summary = {'addresses': 0, 'priced_new': 0, 'checked': 0, 'interactions_logged': 0}

        try:
            # Build address list: watchlist + recent traders up to top
            addresses = []
            try:
                wl = smart_money_repository.get_smart_money_watchlist(min_sharpe=0.0, limit=top) or []
                addresses.extend([r.get('address') for r in wl if r.get('address')])
            except Exception:
                pass
            if len(addresses) < top:
                pool = smart_money_repository.get_recent_traders(hours_back=hours, limit=max(top * 2, 100))
                for a in pool:
                    if a not in addresses:
                        addresses.append(a)
                    if len(addresses) >= top:
                        break
            summary['addresses'] = len(addresses)

            # 1) Backfill interactions
            logged_total = 0
            for i, addr in enumerate(addresses, 1):
                try:
                    logged = smart_money_discovery.backfill_address_interactions(addr, days=activity_days)
                    logged_total += int(logged)
                except Exception as e:
                    # Retry once on connection termination
                    if 'ConnectionTerminated' in str(e):
                        try:
                            time.sleep(0.2)
                            logged = smart_money_discovery.backfill_address_interactions(addr, days=activity_days)
                            logged_total += int(logged)
                        except Exception:
                            pass
                if i % 25 == 0:
                    time.sleep(0.03)
            summary['interactions_logged'] = logged_total

            # 2) Price
            priced_new = 0
            checked = 0
            for i, addr in enumerate(addresses, 1):
                res = pricing_service.price_address(addr, days=price_days, time_budget_sec=time_budget, debug=False)
                priced_new += int(res.get('priced_new', 0))
                checked += int(res.get('checked', 0))
                if i % 25 == 0:
                    time.sleep(0.03)
            summary['priced_new'] = priced_new
            summary['checked'] = checked

            # 3) Metrics
            for i, addr in enumerate(addresses, 1):
                _ = metrics_service.compute_for_address(addr, days=metrics_days)
                if i % 25 == 0:
                    time.sleep(0.03)

            # 4) Activity rollup
            for i, addr in enumerate(addresses, 1):
                _ = smart_money_discovery.get_activity_metrics(addr)
                if i % 25 == 0:
                    time.sleep(0.03)

            # Log complete
            if job_id is not None:
                client.table('job_logs').update({
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat(),
                    'summary': summary,
                }).eq('id', job_id).execute()

            self.send_json_response({'ok': True, 'job_id': job_id, 'summary': summary})
        except Exception as e:
            if job_id is not None:
                try:
                    client.table('job_logs').update({
                        'status': 'failed',
                        'completed_at': datetime.now().isoformat(),
                        'summary': {'error': str(e), **summary},
                    }).eq('id', job_id).execute()
                except Exception:
                    pass
            self.send_json_response({'error': str(e), 'summary': summary}, status=500)
    
    def check_dev_auth(self):
        """Check for dev authorization header"""
        auth_header = self.headers.get('Authorization', '')
        # Simple dev token - in production this would be more secure
        return auth_header == 'Bearer whale-dev-2024'

    def serve_health_db_write(self):
        """Protected write-check: verifies Supabase write & cleanup (dev-only)"""
        start_time = time.time()
        response = {
            'endpoint': '/health/db-write',
            'timestamp': datetime.now().isoformat(),
            'status': 'unhealthy'
        }
        
        # Cooldown enforcement
        now = time.time()
        wait_left = max(0, int(self._write_health_cooldown - (now - self.__class__._last_db_write_check_ts)))
        if wait_left > 0:
            response.update({'status': 'degraded', 'warning': f'Cooldown active: retry in {wait_left}s'})
            self.send_json_response(response, status=429)
            return
        
        # Preconditions
        if not supabase_client:
            response.update({'error': 'Supabase client not initialized'})
            self.send_json_response(response, status=503)
            return
        
        client = supabase_client.get_client()
        test_tx = f"healthcheck-{int(now)}"
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
            # cleanup
            client.table('dex_interactions').delete().eq('tx_hash', test_tx).execute()
            self.__class__._last_db_write_check_ts = now
            response.update({'status': 'healthy', 'write': 'ok', 'cleanup': 'ok'})
        except Exception as e:
            response.update({'status': 'unhealthy', 'error': str(e)})
            # keep last check timestamp unchanged on failure
        
        response['response_time_ms'] = round((time.time() - start_time) * 1000, 1)
        self.send_json_response(response, status=200 if wrote else 503)
    
    def serve_scan_trigger(self):
        """Protected endpoint to trigger whale scanning"""
        if not whale_scanner_service:
            self.send_json_response({
                'error': 'Whale scanner service not available'
            }, status=503)
            return
        
        try:
            # Run single scan
            result = whale_scanner_service.run_full_scan()
            
            response = {
                'success': True,
                'message': 'Whale scan completed',
                'scan_results': result,
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_json_response({
                'success': False,
                'error': f'Scan failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }, status=500)
    
    def serve_scan_status(self):
        """Get current scanning status"""
        if not whale_scanner_service:
            self.send_json_response({
                'error': 'Whale scanner service not available'
            }, status=503)
            return
        
        status = whale_scanner_service.get_scan_status()
        status['timestamp'] = datetime.now().isoformat()
        
        self.send_json_response(status)
    
    def log_request_timing(self, path):
        """Log request timing for monitoring and alerting"""
        if self.request_start_time is None:
            return
        
        duration_ms = (time.time() - self.request_start_time) * 1000
        
        # Simple logging format for easy parsing
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {path} - {duration_ms:.1f}ms"
        
        # Print to stdout (can be captured by monitoring tools)
        print(f"REQUEST_TIMING: {log_entry}")
        
        # Track slow requests (potential issues)
        if duration_ms > 500:  # > 500ms is slow
            print(f"SLOW_REQUEST: {log_entry}")
            
        # Track very slow requests (critical issues)  
        if duration_ms > 2000:  # > 2s is very slow
            print(f"CRITICAL_SLOW: {log_entry}")
    
    # REMOVED: serve_scan() method - prevents user-triggered API rate limit exhaustion
    # Background job will handle whale data collection independently
    
    def get_whale_data(self):
        """Get whale data with caching"""
        now = time.time()
        
        # Check cache
        if (self.cache_timestamp and 
            now - self.cache_timestamp < self.cache_duration and
            self.whale_cache):
            return self.whale_cache
        
        # Get fresh data from database
        db_whales = self.db.get_top_whales(limit=50)
        
        # Format response with smart display logic
        whale_list = []
        for db_whale in db_whales:
            # Get enhanced whale info using cached data only (NO API CALLS)
            enhanced_whale = self.whale_service.get_whale_info_cached(
                db_whale['address'],
                cached_balance_eth=db_whale.get('balance_eth', 0),
                cached_balance_usd=db_whale.get('balance_usd', 0),
                last_updated=db_whale.get('last_updated_at')
            )
            
            # Get ROI scores from nested relationship
            roi_scores = db_whale.get('whale_roi_scores', [])
            roi_data = roi_scores[0] if roi_scores else {}
            
            whale_data = {
                'address': db_whale['address'],
                'name': enhanced_whale.get('name', db_whale['label']),  # Legacy field
                'display_name': enhanced_whale.get('display_name', enhanced_whale.get('name')),
                'description': enhanced_whale.get('description', ''),
                'ens': enhanced_whale.get('ens', ''),
                'entity_type': enhanced_whale.get('entity_type', 'Unknown'),
                'category': enhanced_whale.get('category', 'Unknown'),
                'balance_eth': float(db_whale['balance_eth'] or 0),
                'balance_usd': float(db_whale['balance_eth'] or 0) * 2000,
                'composite_score': float(roi_data.get('composite_score', 0)),
                'total_trades': int(roi_data.get('total_trades', 0)),
                'avg_roi_percent': float(roi_data.get('avg_roi_percent', 0)),
                'win_rate_percent': float(roi_data.get('win_rate_percent', 0))
            }
            whale_list.append(whale_data)
        
        response = {
            'whales': whale_list,
            'count': len(whale_list),
            'generated_at': datetime.now().isoformat()
        }
        
        # Cache response
        self.whale_cache = response
        self.cache_timestamp = now
        
        return response
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    

if __name__ == "__main__":
    print("🔧 API Handlers ready")
    print("Use with HTTP server to serve whale tracking API")
