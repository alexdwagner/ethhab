#!/usr/bin/env python3
"""
Enhanced ETHhab Intelligence Web App with ROI Scoring
Integrates ROI scoring with existing whale tracking
"""

import json
import time
import os
import sqlite3
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import threading

# Try to import existing components
try:
    from minimal_whale_scanner import MinimalWhaleScanner
    from intelligence_aggregator import IntelligenceAggregator
    SCANNER_AVAILABLE = True
except ImportError:
    print("⚠️  Scanner modules not available - using ROI data only")
    SCANNER_AVAILABLE = False

class ROIEnhancedHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Use unified database
        self.db_path = "whale_tracker.db"
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_html().encode())
        
        elif self.path == '/api/roi-whales':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Get whales with ROI scores
            roi_whales = self.get_roi_whale_data()
            self.wfile.write(json.dumps(roi_whales).encode())
        
        elif self.path == '/api/top-performers':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Get top performing whales by ROI
            top_performers = self.get_top_performers()
            self.wfile.write(json.dumps(top_performers).encode())
        
        else:
            self.send_error(404)

    def get_roi_whale_data(self):
        """Get whale data with ROI scores"""
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    wallet_address,
                    composite_score,
                    roi_score,
                    volume_score, 
                    consistency_score,
                    risk_score,
                    activity_score,
                    efficiency_score,
                    avg_roi_percent,
                    total_trades,
                    win_rate_percent,
                    total_volume_usd,
                    calculated_at
                FROM whale_roi_scores 
                ORDER BY composite_score DESC 
                LIMIT 50
            """)
            
            rows = cursor.fetchall()
            
            whales = []
            for row in rows:
                whale = {
                    'address': row[0],
                    'composite_score': float(row[1]),
                    'scores': {
                        'roi': float(row[2]),
                        'volume': float(row[3]),
                        'consistency': float(row[4]),
                        'risk': float(row[5]),
                        'activity': float(row[6]),
                        'efficiency': float(row[7])
                    },
                    'metrics': {
                        'avg_roi_percent': float(row[8]),
                        'total_trades': int(row[9]),
                        'win_rate_percent': float(row[10]),
                        'total_volume_usd': float(row[11])
                    },
                    'calculated_at': row[12],
                    'rank': len(whales) + 1
                }
                whales.append(whale)
            
            return {
                'whales': whales,
                'total_count': len(whales),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def get_top_performers(self):
        """Get top performing whales with detailed metrics"""
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get top 10 by different categories
            categories = {
                'highest_roi': 'ORDER BY composite_score DESC LIMIT 10',
                'most_active': 'ORDER BY total_trades DESC LIMIT 10', 
                'most_consistent': 'ORDER BY win_rate_percent DESC LIMIT 10',
                'highest_volume': 'ORDER BY total_volume_usd DESC LIMIT 10'
            }
            
            results = {}
            
            for category, order_clause in categories.items():
                cursor.execute(f"""
                    SELECT 
                        wallet_address,
                        composite_score,
                        avg_roi_percent,
                        total_trades,
                        win_rate_percent,
                        total_volume_usd,
                        sharpe_ratio,
                        max_drawdown_percent
                    FROM whale_roi_scores 
                    {order_clause}
                """)
                
                rows = cursor.fetchall()
                
                category_whales = []
                for row in rows:
                    whale = {
                        'address': row[0],
                        'composite_score': float(row[1]),
                        'avg_roi_percent': float(row[2]),
                        'total_trades': int(row[3]),
                        'win_rate_percent': float(row[4]),
                        'total_volume_usd': float(row[5]),
                        'sharpe_ratio': float(row[6]),
                        'max_drawdown_percent': float(row[7])
                    }
                    category_whales.append(whale)
                
                results[category] = category_whales
            
            return {
                'categories': results,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def get_html(self):
        """Generate HTML dashboard with ROI integration"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>🐋 Whale Intelligence Dashboard with ROI Scoring</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; min-height: 100vh;
        }}
        .header {{ 
            text-align: center; margin-bottom: 30px;
            background: rgba(0,0,0,0.2); padding: 20px; border-radius: 10px;
        }}
        .stats-grid {{ 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; margin-bottom: 30px;
        }}
        .stat-card {{ 
            background: rgba(255,255,255,0.1); padding: 20px; 
            border-radius: 10px; text-align: center; backdrop-filter: blur(10px);
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
        .whale-list {{ 
            background: rgba(255,255,255,0.1); border-radius: 10px; 
            padding: 20px; backdrop-filter: blur(10px);
        }}
        .whale-item {{ 
            display: flex; justify-content: space-between; align-items: center;
            padding: 15px; margin: 10px 0; 
            background: rgba(255,255,255,0.1); border-radius: 8px;
        }}
        .whale-address {{ 
            font-family: monospace; font-size: 14px; 
            background: rgba(0,0,0,0.3); padding: 5px 10px; border-radius: 5px;
        }}
        .roi-score {{ 
            font-size: 1.5em; font-weight: bold; 
            padding: 5px 15px; border-radius: 20px;
        }}
        .score-excellent {{ background: #4CAF50; }}
        .score-good {{ background: #FF9800; }}
        .score-average {{ background: #2196F3; }}
        .score-poor {{ background: #f44336; }}
        .metrics {{ font-size: 0.9em; opacity: 0.8; }}
        .loading {{ text-align: center; padding: 50px; }}
        .tabs {{ 
            display: flex; margin-bottom: 20px; 
            background: rgba(0,0,0,0.2); border-radius: 10px; padding: 5px;
        }}
        .tab {{ 
            flex: 1; padding: 10px; text-align: center; cursor: pointer;
            border-radius: 8px; transition: all 0.3s;
        }}
        .tab.active {{ background: rgba(255,255,255,0.2); }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🐋 Whale Intelligence Dashboard</h1>
        <h2>📊 Enhanced with ROI Scoring Algorithm v2</h2>
        <p>Real-time whale performance tracking with comprehensive ROI analysis</p>
    </div>

    <div class="tabs">
        <div class="tab active" onclick="showTab('roi-whales')">🎯 ROI Rankings</div>
        <div class="tab" onclick="showTab('top-performers')">🏆 Top Performers</div>
        <div class="tab" onclick="showTab('analytics')">📈 Analytics</div>
    </div>

    <div id="roi-whales" class="tab-content active">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="total-whales">-</div>
                <div>Total Whales Tracked</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-roi">-</div>
                <div>Average ROI Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-volume">-</div>
                <div>Total Volume Tracked</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="active-traders">-</div>
                <div>Active Traders</div>
            </div>
        </div>

        <div class="whale-list">
            <h3>🐋 Whale ROI Rankings</h3>
            <div id="whale-data" class="loading">Loading whale data...</div>
        </div>
    </div>

    <div id="top-performers" class="tab-content">
        <div id="performers-data" class="loading">Loading top performers...</div>
    </div>

    <div id="analytics" class="tab-content">
        <div class="stat-card">
            <h3>📊 System Statistics</h3>
            <p>ROI Scoring Algorithm: Event-sourced with FIFO accounting</p>
            <p>Price Oracle: Multi-source (CoinGecko + On-chain TWAP)</p>
            <p>Risk Metrics: Sharpe ratio, Max drawdown, Volatility</p>
            <p>Update Frequency: Real-time with smart caching</p>
            <p>Database: SQLite with optimized indexing</p>
        </div>
    </div>

    <script>
        let currentTab = 'roi-whales';

        function showTab(tabName) {{
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            currentTab = tabName;
            
            // Load data for the tab
            if (tabName === 'roi-whales') {{
                loadROIWhales();
            }} else if (tabName === 'top-performers') {{
                loadTopPerformers();
            }}
        }}

        function getROIScoreClass(score) {{
            if (score >= 70) return 'score-excellent';
            if (score >= 50) return 'score-good'; 
            if (score >= 30) return 'score-average';
            return 'score-poor';
        }}

        function formatNumber(num) {{
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toString();
        }}

        function loadROIWhales() {{
            fetch('/api/roi-whales')
                .then(response => response.json())
                .then(data => {{
                    if (data.error) {{
                        document.getElementById('whale-data').innerHTML = `
                            <div style="text-align: center; color: #f44336;">
                                ⚠️ ${{data.error}}<br>
                                <small>Run setup_roi_scoring.py to initialize</small>
                            </div>`;
                        return;
                    }}
                    
                    const whales = data.whales || [];
                    
                    // Update stats
                    document.getElementById('total-whales').textContent = whales.length;
                    const avgROI = whales.length ? 
                        (whales.reduce((sum, w) => sum + w.composite_score, 0) / whales.length).toFixed(1) : 0;
                    document.getElementById('avg-roi').textContent = avgROI;
                    
                    const totalVol = whales.reduce((sum, w) => sum + (w.metrics?.total_volume_usd || 0), 0);
                    document.getElementById('total-volume').textContent = '$' + formatNumber(totalVol);
                    
                    const activeTraders = whales.filter(w => (w.metrics?.total_trades || 0) > 10).length;
                    document.getElementById('active-traders').textContent = activeTraders;
                    
                    // Render whale list
                    const whaleHtml = whales.map(whale => `
                        <div class="whale-item">
                            <div>
                                <div class="whale-address">${{whale.address}}</div>
                                <div class="metrics">
                                    Trades: ${{whale.metrics?.total_trades || 0}} | 
                                    Win Rate: ${{(whale.metrics?.win_rate_percent || 0).toFixed(1)}}% |
                                    Volume: $${{formatNumber(whale.metrics?.total_volume_usd || 0)}}
                                </div>
                            </div>
                            <div class="roi-score ${{getROIScoreClass(whale.composite_score)}}">
                                ${{whale.composite_score.toFixed(1)}}
                            </div>
                        </div>
                    `).join('');
                    
                    document.getElementById('whale-data').innerHTML = whaleHtml || 
                        '<div style="text-align: center;">No whale data available</div>';
                }})
                .catch(error => {{
                    document.getElementById('whale-data').innerHTML = 
                        `<div style="color: #f44336;">Error: ${{error.message}}</div>`;
                }});
        }}

        function loadTopPerformers() {{
            fetch('/api/top-performers')
                .then(response => response.json())
                .then(data => {{
                    if (data.error) {{
                        document.getElementById('performers-data').innerHTML = 
                            `<div style="color: #f44336;">Error: ${{data.error}}</div>`;
                        return;
                    }}
                    
                    const categories = data.categories || {{}};
                    let html = '';
                    
                    for (const [categoryName, whales] of Object.entries(categories)) {{
                        html += `
                            <div class="whale-list">
                                <h3>${{categoryName.replace('_', ' ').toUpperCase()}}</h3>
                                ${{whales.slice(0, 5).map((whale, i) => `
                                    <div class="whale-item">
                                        <div>
                                            <strong>#${{i + 1}}</strong>
                                            <div class="whale-address">${{whale.address}}</div>
                                        </div>
                                        <div class="metrics">
                                            ROI: ${{whale.composite_score.toFixed(1)}} | 
                                            Avg: ${{whale.avg_roi_percent.toFixed(1)}}% |
                                            Trades: ${{whale.total_trades}}
                                        </div>
                                    </div>
                                `).join('')}}
                            </div>
                        `;
                    }}
                    
                    document.getElementById('performers-data').innerHTML = html;
                }})
                .catch(error => {{
                    document.getElementById('performers-data').innerHTML = 
                        `<div style="color: #f44336;">Error: ${{error.message}}</div>`;
                }});
        }}

        // Auto-refresh every 30 seconds
        setInterval(() => {{
            if (currentTab === 'roi-whales') loadROIWhales();
            else if (currentTab === 'top-performers') loadTopPerformers();
        }}, 30000);

        // Load initial data
        loadROIWhales();
    </script>
</body>
</html>
"""

def run_roi_enhanced_server(port=8081):
    """Run the ROI-enhanced whale intelligence server"""
    print(f"🚀 Starting ROI-Enhanced Whale Intelligence Server on port {port}")
    print(f"🌐 Dashboard: http://localhost:{port}")
    print("📊 Features: ROI Scoring, Performance Analytics, Smart Rankings")
    print("-" * 60)
    
    server = HTTPServer(('localhost', port), ROIEnhancedHandler)
    
    # Open browser
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{port}')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        print("🎯 ROI scoring integration active!")
        print("📈 Real-time whale performance tracking enabled")
        print("⚡ Smart caching and auto-refresh enabled")
        print("\nPress Ctrl+C to stop...")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down ROI-Enhanced Intelligence Server...")
        server.shutdown()

if __name__ == "__main__":
    run_roi_enhanced_server()