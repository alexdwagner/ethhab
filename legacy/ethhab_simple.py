#!/usr/bin/env python3
"""
ETHhab Simple Web Server
Basic HTML interface for whale tracking
"""

import json
import time
from datetime import datetime
from minimal_whale_scanner import MinimalWhaleScanner
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import webbrowser
import threading

class ETHhabHTTPHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_html().encode())
        elif self.path == '/api/whales':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Get whale data
            scanner = MinimalWhaleScanner()
            whale_data = []
            
            for address in scanner.whale_addresses:
                try:
                    balance = scanner.get_eth_balance(address)
                    transactions = scanner.get_recent_transactions(address, 5)
                    
                    # Calculate volume
                    volume = sum(int(tx['value'])/1e18 for tx in transactions)
                    
                    # Determine tier
                    if balance >= 100000:
                        tier = "Institutional"
                        emoji = "🏛️"
                    elif balance >= 10000:
                        tier = "Mega Whale"
                        emoji = "🐋"
                    elif balance >= 1000:
                        tier = "Large Whale"
                        emoji = "🦈"
                    else:
                        tier = "Mini Whale"
                        emoji = "🐟"
                    
                    whale_data.append({
                        'address': address,
                        'balance': round(balance, 2),
                        'tier': tier,
                        'emoji': emoji,
                        'volume': round(volume, 2),
                        'transactions': len(transactions)
                    })
                    
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    print(f"Error scanning {address}: {e}")
            
            self.wfile.write(json.dumps(whale_data).encode())
        else:
            super().do_GET()
    
    def get_html(self):
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETHhab 🐋 - Ethereum Whale Tracker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-style: italic;
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .controls {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .scan-btn {
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            border: none;
            padding: 15px 30px;
            font-size: 1.1rem;
            color: white;
            border-radius: 25px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .scan-btn:hover {
            transform: scale(1.05);
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .metric-card h3 {
            font-size: 2rem;
            margin-bottom: 5px;
        }
        
        .whale-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .whale-card {
            background: rgba(255,255,255,0.15);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.2s;
        }
        
        .whale-card:hover {
            transform: translateY(-5px);
        }
        
        .whale-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .whale-tier {
            font-size: 1.1rem;
            font-weight: bold;
        }
        
        .whale-emoji {
            font-size: 1.5rem;
        }
        
        .whale-info {
            margin-bottom: 10px;
        }
        
        .whale-address {
            font-family: monospace;
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .whale-balance {
            font-size: 1.3rem;
            font-weight: bold;
            color: #f1c40f;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
        }
        
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top: 4px solid white;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            opacity: 0.8;
        }
        
        .winners-board {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 30px 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .winners-board h2 {
            text-align: center;
            margin-bottom: 20px;
            font-size: 1.8rem;
            color: #f1c40f;
        }
        
        .whale-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        
        .whale-table th,
        .whale-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        
        .whale-table th {
            background: rgba(255,255,255,0.2);
            font-weight: bold;
            cursor: pointer;
            user-select: none;
            position: relative;
            transition: background 0.2s;
        }
        
        .whale-table th:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .whale-table th.sortable::after {
            content: ' ↕️';
            font-size: 0.8rem;
        }
        
        .whale-table th.sort-asc::after {
            content: ' ⬆️';
        }
        
        .whale-table th.sort-desc::after {
            content: ' ⬇️';
        }
        
        .whale-table tr:nth-child(even) {
            background: rgba(255,255,255,0.05);
        }
        
        .whale-table tr:hover {
            background: rgba(255,255,255,0.15);
        }
        
        .rank-cell {
            font-weight: bold;
            color: #f1c40f;
            text-align: center;
            width: 50px;
        }
        
        .tier-cell {
            text-align: center;
            font-size: 1.2rem;
        }
        
        .address-cell {
            font-family: monospace;
            font-size: 0.9rem;
        }
        
        .balance-cell {
            font-weight: bold;
            color: #2ecc71;
            text-align: right;
        }
        
        .volume-cell {
            color: #e74c3c;
            text-align: right;
        }
        
        .usd-cell {
            color: #f39c12;
            text-align: right;
        }
        
        @media (max-width: 768px) {
            .whale-table {
                font-size: 0.8rem;
            }
            
            .whale-table th,
            .whale-table td {
                padding: 8px 4px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🐋 ETHhab</h1>
            <p>"Call me ETHhab" - Hunting Ethereum Whales</p>
        </header>
        
        <div class="controls">
            <button class="scan-btn" onclick="loadWhales()">🔄 Scan Whales Now</button>
        </div>
        
        <div id="summary" class="summary"></div>
        
        <div class="winners-board">
            <h2>🏆 Whale Winners Board</h2>
            <div style="text-align: center; margin-bottom: 15px;">
                <span style="opacity: 0.8;">Click column headers to sort • Hover rows for details</span>
            </div>
            <table class="whale-table" id="whaleTable">
                <thead>
                    <tr>
                        <th class="sortable" data-sort="rank">#</th>
                        <th class="sortable" data-sort="tier">Tier</th>
                        <th class="sortable" data-sort="address">Address</th>
                        <th class="sortable" data-sort="balance">ETH Balance</th>
                        <th class="sortable" data-sort="usd">USD Value</th>
                        <th class="sortable" data-sort="volume">Recent Volume</th>
                        <th class="sortable" data-sort="transactions">Txns</th>
                    </tr>
                </thead>
                <tbody id="whaleTableBody">
                    <tr>
                        <td colspan="7" style="text-align: center; padding: 40px;">
                            <div class="spinner"></div>
                            <p>Loading whale leaderboard...</p>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div id="whales" class="whale-grid"></div>
        
        <footer class="footer">
            <p>🐋 ETHhab - Built with ❤️ for whale hunters</p>
            <p>Last updated: <span id="lastUpdate">Never</span></p>
        </footer>
    </div>

    <script>
        let whaleData = [];
        let currentSort = { column: 'balance', direction: 'desc' };
        
        function formatNumber(num) {
            return new Intl.NumberFormat().format(Math.round(num));
        }
        
        function formatAddress(address) {
            return address.substring(0, 10) + '...' + address.substring(address.length - 6);
        }
        
        function formatETH(amount) {
            if (amount >= 1000000) {
                return (amount / 1000000).toFixed(1) + 'M';
            } else if (amount >= 1000) {
                return (amount / 1000).toFixed(1) + 'K';
            } else {
                return amount.toFixed(2);
            }
        }
        
        function formatUSD(amount) {
            const usd = amount * 3000; // ETH price
            if (usd >= 1000000000) {
                return '$' + (usd / 1000000000).toFixed(1) + 'B';
            } else if (usd >= 1000000) {
                return '$' + (usd / 1000000).toFixed(1) + 'M';
            } else if (usd >= 1000) {
                return '$' + (usd / 1000).toFixed(1) + 'K';
            } else {
                return '$' + usd.toFixed(0);
            }
        }
        
        function showLoading() {
            document.getElementById('whales').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>🐋 Scanning the blockchain for whales...</p>
                </div>
            `;
        }
        
        function updateSummary() {
            const totalWhales = whaleData.length;
            const totalEth = whaleData.reduce((sum, whale) => sum + whale.balance, 0);
            const avgBalance = totalEth / totalWhales;
            const totalVolume = whaleData.reduce((sum, whale) => sum + whale.volume, 0);
            
            document.getElementById('summary').innerHTML = `
                <div class="metric-card">
                    <h3>🐋 ${totalWhales}</h3>
                    <p>Total Whales</p>
                </div>
                <div class="metric-card">
                    <h3>💰 ${formatNumber(totalEth)}</h3>
                    <p>Total ETH</p>
                </div>
                <div class="metric-card">
                    <h3>📈 ${formatNumber(avgBalance)}</h3>
                    <p>Avg Balance</p>
                </div>
                <div class="metric-card">
                    <h3>🔄 ${formatNumber(totalVolume)}</h3>
                    <p>Recent Volume</p>
                </div>
            `;
        }
        
        function sortWhales(column) {
            // Toggle direction if same column, otherwise default to desc
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'desc' ? 'asc' : 'desc';
            } else {
                currentSort.column = column;
                currentSort.direction = column === 'address' ? 'asc' : 'desc';
            }
            
            // Sort the data
            whaleData.sort((a, b) => {
                let aVal, bVal;
                
                switch(column) {
                    case 'balance':
                        aVal = a.balance;
                        bVal = b.balance;
                        break;
                    case 'volume':
                        aVal = a.volume;
                        bVal = b.volume;
                        break;
                    case 'transactions':
                        aVal = a.transactions;
                        bVal = b.transactions;
                        break;
                    case 'usd':
                        aVal = a.balance * 3000;
                        bVal = b.balance * 3000;
                        break;
                    case 'tier':
                        const tierOrder = {'Institutional': 4, 'Mega Whale': 3, 'Large Whale': 2, 'Mini Whale': 1};
                        aVal = tierOrder[a.tier];
                        bVal = tierOrder[b.tier];
                        break;
                    case 'address':
                        aVal = a.address.toLowerCase();
                        bVal = b.address.toLowerCase();
                        break;
                    default:
                        return 0;
                }
                
                if (currentSort.direction === 'asc') {
                    return aVal > bVal ? 1 : -1;
                } else {
                    return aVal < bVal ? 1 : -1;
                }
            });
            
            updateTable();
            updateSortHeaders();
        }
        
        function updateSortHeaders() {
            // Reset all headers
            document.querySelectorAll('.whale-table th').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
                th.classList.add('sortable');
            });
            
            // Set current sort header
            const currentHeader = document.querySelector(`[data-sort="${currentSort.column}"]`);
            if (currentHeader) {
                currentHeader.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        }
        
        function updateTable() {
            const tableBody = document.getElementById('whaleTableBody');
            
            const rowsHtml = whaleData.map((whale, index) => {
                const rank = index + 1;
                let rankDisplay = rank;
                
                // Add trophy emojis for top 3
                if (rank === 1) rankDisplay = '🥇';
                else if (rank === 2) rankDisplay = '🥈';
                else if (rank === 3) rankDisplay = '🥉';
                
                return `
                    <tr onclick="showWhaleDetails('${whale.address}')" style="cursor: pointer;">
                        <td class="rank-cell">${rankDisplay}</td>
                        <td class="tier-cell">${whale.emoji}</td>
                        <td class="address-cell">${formatAddress(whale.address)}</td>
                        <td class="balance-cell">${formatETH(whale.balance)} ETH</td>
                        <td class="usd-cell">${formatUSD(whale.balance)}</td>
                        <td class="volume-cell">${formatETH(whale.volume)} ETH</td>
                        <td style="text-align: center;">${whale.transactions}</td>
                    </tr>
                `;
            }).join('');
            
            tableBody.innerHTML = rowsHtml;
        }
        
        function showWhaleDetails(address) {
            const whale = whaleData.find(w => w.address === address);
            if (whale) {
                alert(`🐋 Whale Details\\n\\nAddress: ${whale.address}\\nTier: ${whale.tier}\\nBalance: ${formatNumber(whale.balance)} ETH\\nUSD Value: ${formatUSD(whale.balance)}\\nRecent Volume: ${formatNumber(whale.volume)} ETH\\nTransactions: ${whale.transactions}`);
            }
        }
        
        function displayWhales() {
            const whalesHtml = whaleData.map(whale => `
                <div class="whale-card">
                    <div class="whale-header">
                        <span class="whale-tier">${whale.tier}</span>
                        <span class="whale-emoji">${whale.emoji}</span>
                    </div>
                    <div class="whale-info">
                        <div class="whale-address">${formatAddress(whale.address)}</div>
                        <div class="whale-balance">${formatNumber(whale.balance)} ETH</div>
                    </div>
                    <div class="whale-info">
                        <div>💼 Recent Volume: ${formatNumber(whale.volume)} ETH</div>
                        <div>📊 Transactions: ${whale.transactions}</div>
                        <div>💵 USD Value: $${formatNumber(whale.balance * 3000)}</div>
                    </div>
                </div>
            `).join('');
            
            document.getElementById('whales').innerHTML = whalesHtml;
        }
        
        async function loadWhales() {
            showLoading();
            
            try {
                const response = await fetch('/api/whales');
                whaleData = await response.json();
                
                // Sort by balance (default)
                sortWhales('balance');
                
                updateSummary();
                displayWhales();
                
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error loading whale data:', error);
                document.getElementById('whales').innerHTML = `
                    <div class="loading">
                        <p>❌ Error loading whale data. Check console for details.</p>
                    </div>
                `;
                document.getElementById('whaleTableBody').innerHTML = `
                    <tr>
                        <td colspan="7" style="text-align: center; padding: 20px; color: #e74c3c;">
                            ❌ Error loading whale data
                        </td>
                    </tr>
                `;
            }
        }
        
        // Load whales on page load
        window.addEventListener('load', () => {
            loadWhales();
            
            // Add click handlers to table headers
            document.querySelectorAll('.whale-table th[data-sort]').forEach(th => {
                th.addEventListener('click', () => {
                    const sortColumn = th.getAttribute('data-sort');
                    if (sortColumn !== 'rank') {
                        sortWhales(sortColumn);
                    }
                });
            });
        });
        
        // Auto-refresh every 5 minutes
        setInterval(loadWhales, 300000);
    </script>
</body>
</html>
        '''

def start_server():
    """Start the ETHhab web server"""
    PORT = 8000
    
    with socketserver.TCPServer(("", PORT), ETHhabHTTPHandler) as httpd:
        print(f"🐋 ETHhab server starting on http://localhost:{PORT}")
        print("🌐 Opening browser...")
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(2)
            webbrowser.open(f'http://localhost:{PORT}')
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\n🛑 ETHhab server stopped")

if __name__ == "__main__":
    start_server()