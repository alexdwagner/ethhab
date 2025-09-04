#!/usr/bin/env python3
"""
ROI-Based Scoring Algorithm v2 (Event-Sourced)
Comprehensive whale performance tracking with proper accounting
"""

import json
import sqlite3
import statistics
import math
import time
import requests
from datetime import datetime, timedelta, date
from dataclasses import dataclass, asdict
from collections import defaultdict
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
from web3 import Web3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Schema Creation
def create_roi_tracking_schema(db_path: str):
    """Create database schema for event-sourced ROI tracking"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Raw blockchain fills (event-sourced)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_fills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            token_address VARCHAR(42) NOT NULL,
            token_symbol VARCHAR(20) NOT NULL,
            token_decimals INTEGER NOT NULL,
            direction VARCHAR(4) NOT NULL, -- BUY/SELL
            amount DECIMAL(36,18) NOT NULL,
            price_usd DECIMAL(18,8),
            value_usd DECIMAL(18,2),
            block_number INTEGER NOT NULL,
            block_timestamp TIMESTAMP NOT NULL,
            transaction_hash VARCHAR(66) NOT NULL,
            log_index INTEGER NOT NULL,
            gas_cost_usd DECIMAL(18,2),
            counterparty VARCHAR(42),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_wallet_time ON token_fills(wallet_address, block_timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_token_time ON token_fills(token_address, block_timestamp)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fills_unique ON token_fills(transaction_hash, log_index)")
    
    # Closed trade lots (FIFO accounting)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS closed_trade_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            token_address VARCHAR(42) NOT NULL,
            token_symbol VARCHAR(20) NOT NULL,
            trade_amount DECIMAL(36,18) NOT NULL,
            entry_price_usd DECIMAL(18,8) NOT NULL,
            exit_price_usd DECIMAL(18,8) NOT NULL,
            entry_timestamp TIMESTAMP NOT NULL,
            exit_timestamp TIMESTAMP NOT NULL,
            hold_duration_days INTEGER NOT NULL,
            entry_value_usd DECIMAL(18,2) NOT NULL,
            exit_value_usd DECIMAL(18,2) NOT NULL,
            entry_gas_cost_usd DECIMAL(18,2) NOT NULL,
            exit_gas_cost_usd DECIMAL(18,2) NOT NULL,
            gross_pnl_usd DECIMAL(18,2) NOT NULL,
            net_pnl_usd DECIMAL(18,2) NOT NULL,
            roi_percent DECIMAL(10,4) NOT NULL,
            entry_fill_id INTEGER,
            exit_fill_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_wallet_exit ON closed_trade_lots(wallet_address, exit_timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lots_roi ON closed_trade_lots(roi_percent DESC)")
    
    # Daily equity snapshots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_equity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            date DATE NOT NULL,
            portfolio_value_usd DECIMAL(18,2) NOT NULL,
            realized_pnl_usd DECIMAL(18,2) NOT NULL,
            unrealized_pnl_usd DECIMAL(18,2) NOT NULL,
            total_invested_usd DECIMAL(18,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_equity_wallet_date ON daily_equity(wallet_address, date)")
    
    # Performance metrics cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address VARCHAR(42) NOT NULL,
            timeframe_days INTEGER NOT NULL,
            total_trades INTEGER NOT NULL,
            total_net_pnl_usd DECIMAL(18,2) NOT NULL,
            avg_roi_percent DECIMAL(10,4) NOT NULL,
            median_roi_percent DECIMAL(10,4) NOT NULL,
            win_rate_percent DECIMAL(10,4) NOT NULL,
            sharpe_ratio DECIMAL(10,4) NOT NULL,
            max_drawdown_percent DECIMAL(10,4) NOT NULL,
            avg_hold_days DECIMAL(10,2) NOT NULL,
            total_volume_usd DECIMAL(18,2) NOT NULL,
            gas_efficiency_percent DECIMAL(10,4) NOT NULL,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_wallet ON performance_metrics(wallet_address)")
    
    conn.commit()
    conn.close()

@dataclass
class Fill:
    """Individual token fill from blockchain events"""
    wallet_address: str
    token_address: str
    token_symbol: str
    token_decimals: int
    direction: str  # BUY/SELL
    amount: float
    price_usd: float
    value_usd: float
    block_number: int
    block_timestamp: datetime
    transaction_hash: str
    log_index: int
    gas_cost_usd: float
    counterparty: str
    id: Optional[int] = None

@dataclass
class TradeLot:
    """Individual trade lot (FIFO accounting)"""
    wallet_address: str
    token_address: str
    token_symbol: str
    entry_amount: float
    remaining_amount: float
    entry_price_usd: float
    entry_value_usd: float
    entry_timestamp: datetime
    entry_gas_cost_usd: float
    entry_fill: Fill

@dataclass
class ClosedTradeLot:
    """Completed trade with full P&L accounting"""
    wallet_address: str
    token_address: str
    token_symbol: str
    trade_amount: float
    entry_price_usd: float
    exit_price_usd: float
    entry_timestamp: datetime
    exit_timestamp: datetime
    hold_duration_days: int
    entry_value_usd: float
    exit_value_usd: float
    entry_gas_cost_usd: float
    exit_gas_cost_usd: float
    gross_pnl_usd: float
    net_pnl_usd: float
    roi_percent: float
    entry_fill: Fill
    exit_fill: Fill
    id: Optional[int] = None

class PriceOracle:
    """Multi-source price oracle with on-chain fallback"""
    
    def __init__(self, web3_provider: Web3):
        self.w3 = web3_provider
        self.price_cache = {}
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        self.rate_limit_delay = 1.2  # Seconds between API calls
        self.last_api_call = 0
        
    def get_price_at_block(self, token_address: str, block_number: int) -> Optional[float]:
        """Get token price at specific block"""
        cache_key = f"{token_address}_{block_number}"
        
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        # Get block timestamp
        try:
            block = self.w3.eth.get_block(block_number)
            block_timestamp = datetime.fromtimestamp(block['timestamp'])
        except Exception as e:
            logger.error(f"Error getting block {block_number}: {e}")
            return None
        
        # Try CoinGecko for historical price
        price = self.get_coingecko_price_at_date(token_address, block_timestamp.date())
        
        if price:
            self.price_cache[cache_key] = price
        
        return price
    
    def get_coingecko_price_at_date(self, token_address: str, target_date: date) -> Optional[float]:
        """Get token price from CoinGecko at specific date"""
        # Rate limiting
        time_since_last = time.time() - self.last_api_call
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        try:
            date_str = target_date.strftime("%d-%m-%Y")
            url = f"{self.coingecko_api}/coins/ethereum/contract/{token_address}/history"
            params = {'date': date_str}
            
            response = requests.get(url, params=params, timeout=10)
            self.last_api_call = time.time()
            
            if response.status_code == 200:
                data = response.json()
                if 'market_data' in data and 'current_price' in data['market_data']:
                    return data['market_data']['current_price']['usd']
            elif response.status_code == 429:
                logger.warning("CoinGecko rate limit hit, waiting...")
                time.sleep(60)
                return self.get_coingecko_price_at_date(token_address, target_date)
                
        except Exception as e:
            logger.error(f"CoinGecko price error for {token_address}: {e}")
        
        return None
    
    def get_eth_price_at_block(self, block_number: int) -> Optional[float]:
        """Get ETH price at specific block for gas calculations"""
        # Use WETH address as proxy for ETH price
        weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        return self.get_price_at_block(weth_address, block_number)

class EventProcessor:
    """Process blockchain events to extract token fills"""
    
    def __init__(self, web3_provider: Web3, db_path: str, price_oracle: PriceOracle):
        self.w3 = web3_provider
        self.db_path = db_path
        self.price_oracle = price_oracle
        self.token_cache = {}
        
        # Event signatures
        self.ERC20_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
        self.UNISWAP_V2_SWAP = '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
        self.UNISWAP_V3_SWAP = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
    
    def process_transaction_events(self, tx_hash: str) -> List[Fill]:
        """Extract all token fills from transaction logs"""
        try:
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            tx = self.w3.eth.get_transaction(tx_hash)
            
            # Get ETH price for gas calculations
            eth_price_usd = self.price_oracle.get_eth_price_at_block(tx_receipt['blockNumber']) or 0
            
            # Calculate total gas cost in USD
            gas_cost_usd = (tx['gasPrice'] * tx_receipt['gasUsed'] / 1e18) * eth_price_usd
            
            fills = []
            for log in tx_receipt['logs']:
                fill = self.parse_log_to_fill(log, tx, gas_cost_usd)
                if fill:
                    fills.append(fill)
            
            return fills
            
        except Exception as e:
            logger.error(f"Error processing transaction {tx_hash}: {e}")
            return []
    
    def parse_log_to_fill(self, log, tx, gas_cost_usd: float) -> Optional[Fill]:
        """Parse individual log into a Fill object"""
        if len(log['topics']) == 0:
            return None
            
        topic = log['topics'][0].hex()
        
        if topic == self.ERC20_TRANSFER:
            return self.parse_transfer_event(log, tx, gas_cost_usd)
        
        return None
    
    def parse_transfer_event(self, log, tx, gas_cost_usd: float) -> Optional[Fill]:
        """Parse ERC20 Transfer event into Fill"""
        try:
            if len(log['topics']) < 3:
                return None
                
            token_address = log['address']
            from_address = '0x' + log['topics'][1].hex()[-40:]
            to_address = '0x' + log['topics'][2].hex()[-40:]
            amount_raw = int(log['data'], 16)
            
            # Get token metadata
            token_info = self.get_token_info(token_address)
            if not token_info:
                return None
            
            amount = amount_raw / (10 ** token_info['decimals'])
            
            # Determine direction for wallet
            wallet_address = tx['from'].lower()
            
            if from_address.lower() == wallet_address:
                direction = 'SELL'
                counterparty = to_address
            elif to_address.lower() == wallet_address:
                direction = 'BUY'
                counterparty = from_address
            else:
                return None
            
            # Get token price at block time
            price_usd = self.price_oracle.get_price_at_block(token_address, tx['blockNumber']) or 0
            
            # Get block timestamp
            block = self.w3.eth.get_block(tx['blockNumber'])
            block_timestamp = datetime.fromtimestamp(block['timestamp'])
            
            return Fill(
                wallet_address=wallet_address,
                token_address=token_address,
                token_symbol=token_info['symbol'],
                token_decimals=token_info['decimals'],
                direction=direction,
                amount=amount,
                price_usd=price_usd,
                value_usd=amount * price_usd if price_usd else 0,
                block_number=tx['blockNumber'],
                block_timestamp=block_timestamp,
                transaction_hash=tx['hash'].hex(),
                log_index=log['logIndex'],
                gas_cost_usd=gas_cost_usd,
                counterparty=counterparty
            )
            
        except Exception as e:
            logger.error(f"Error parsing transfer event: {e}")
            return None
    
    def get_token_info(self, token_address: str) -> Optional[Dict[str, any]]:
        """Get token decimals and symbol (cached)"""
        if token_address in self.token_cache:
            return self.token_cache[token_address]
        
        try:
            # Standard ERC20 ABI for decimals and symbol
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[
                    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"}
                ]
            )
            
            decimals = token_contract.functions.decimals().call()
            symbol = token_contract.functions.symbol().call()
            
            token_info = {
                'decimals': decimals,
                'symbol': symbol
            }
            
            self.token_cache[token_address] = token_info
            return token_info
            
        except Exception as e:
            logger.error(f"Error getting token info for {token_address}: {e}")
            return None
    
    def save_fill_to_db(self, fill: Fill) -> int:
        """Save fill to database and return ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO token_fills (
                    wallet_address, token_address, token_symbol, token_decimals,
                    direction, amount, price_usd, value_usd, block_number,
                    block_timestamp, transaction_hash, log_index, gas_cost_usd, counterparty
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fill.wallet_address, fill.token_address, fill.token_symbol,
                fill.token_decimals, fill.direction, fill.amount, fill.price_usd,
                fill.value_usd, fill.block_number, fill.block_timestamp,
                fill.transaction_hash, fill.log_index, fill.gas_cost_usd, fill.counterparty
            ))
            
            fill_id = cursor.lastrowid
            conn.commit()
            return fill_id
            
        except Exception as e:
            logger.error(f"Error saving fill to database: {e}")
            return 0
        finally:
            conn.close()

class LotTracker:
    """Track trade lots using FIFO accounting for accurate P&L"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.open_lots = defaultdict(list)  # wallet -> [(token, Lot), ...]
        self.closed_lots = []
    
    def process_fill(self, fill: Fill):
        """Process a fill and update lots"""
        wallet_lots = self.open_lots[fill.wallet_address]
        
        if fill.direction == 'BUY':
            # Create new lot
            lot = TradeLot(
                wallet_address=fill.wallet_address,
                token_address=fill.token_address,
                token_symbol=fill.token_symbol,
                entry_amount=fill.amount,
                remaining_amount=fill.amount,
                entry_price_usd=fill.price_usd,
                entry_value_usd=fill.value_usd,
                entry_timestamp=fill.block_timestamp,
                entry_gas_cost_usd=fill.gas_cost_usd,
                entry_fill=fill
            )
            wallet_lots.append((fill.token_address, lot))
            
        elif fill.direction == 'SELL':
            # Match against existing lots (FIFO)
            self.process_sell_fill(fill, wallet_lots)
    
    def process_sell_fill(self, sell_fill: Fill, wallet_lots):
        """Process sell fill against existing lots using FIFO"""
        remaining_to_sell = sell_fill.amount
        token_address = sell_fill.token_address
        
        # Find all open lots for this token
        token_lots = [(i, lot) for i, (token, lot) in enumerate(wallet_lots) 
                      if token == token_address and lot.remaining_amount > 0]
        
        # Sort by entry timestamp (FIFO)
        token_lots.sort(key=lambda x: x[1].entry_timestamp)
        
        for lot_index, lot in token_lots:
            if remaining_to_sell <= 0:
                break
            
            # Calculate how much to sell from this lot
            sell_amount = min(remaining_to_sell, lot.remaining_amount)
            sell_ratio = sell_amount / lot.entry_amount
            
            # Calculate P&L for this portion
            entry_cost_usd = lot.entry_value_usd * sell_ratio
            entry_gas_usd = lot.entry_gas_cost_usd * sell_ratio
            exit_value_usd = sell_amount * sell_fill.price_usd
            exit_gas_usd = sell_fill.gas_cost_usd * sell_ratio
            
            gross_pnl = exit_value_usd - entry_cost_usd
            net_pnl = gross_pnl - entry_gas_usd - exit_gas_usd
            
            # Avoid division by zero
            total_cost = entry_cost_usd + entry_gas_usd
            roi_percent = (net_pnl / total_cost * 100) if total_cost > 0 else 0
            
            # Calculate hold duration
            hold_duration = (sell_fill.block_timestamp - lot.entry_timestamp).days
            
            # Create closed lot record
            closed_lot = ClosedTradeLot(
                wallet_address=sell_fill.wallet_address,
                token_address=token_address,
                token_symbol=sell_fill.token_symbol,
                trade_amount=sell_amount,
                entry_price_usd=lot.entry_price_usd,
                exit_price_usd=sell_fill.price_usd,
                entry_timestamp=lot.entry_timestamp,
                exit_timestamp=sell_fill.block_timestamp,
                hold_duration_days=hold_duration,
                entry_value_usd=entry_cost_usd,
                exit_value_usd=exit_value_usd,
                entry_gas_cost_usd=entry_gas_usd,
                exit_gas_cost_usd=exit_gas_usd,
                gross_pnl_usd=gross_pnl,
                net_pnl_usd=net_pnl,
                roi_percent=roi_percent,
                entry_fill=lot.entry_fill,
                exit_fill=sell_fill
            )
            
            self.closed_lots.append(closed_lot)
            self.save_closed_lot_to_db(closed_lot)
            
            # Update remaining lot
            lot.remaining_amount -= sell_amount
            remaining_to_sell -= sell_amount
        
        # Handle oversell
        if remaining_to_sell > 0:
            logger.warning(f"Oversell detected for {sell_fill.token_symbol}: {remaining_to_sell}")
    
    def save_closed_lot_to_db(self, lot: ClosedTradeLot):
        """Save closed lot to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO closed_trade_lots (
                    wallet_address, token_address, token_symbol, trade_amount,
                    entry_price_usd, exit_price_usd, entry_timestamp, exit_timestamp,
                    hold_duration_days, entry_value_usd, exit_value_usd,
                    entry_gas_cost_usd, exit_gas_cost_usd, gross_pnl_usd,
                    net_pnl_usd, roi_percent, entry_fill_id, exit_fill_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lot.wallet_address, lot.token_address, lot.token_symbol, lot.trade_amount,
                lot.entry_price_usd, lot.exit_price_usd, lot.entry_timestamp, lot.exit_timestamp,
                lot.hold_duration_days, lot.entry_value_usd, lot.exit_value_usd,
                lot.entry_gas_cost_usd, lot.exit_gas_cost_usd, lot.gross_pnl_usd,
                lot.net_pnl_usd, lot.roi_percent, lot.entry_fill.id or 0, lot.exit_fill.id or 0
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error saving closed lot to database: {e}")
        finally:
            conn.close()

class EquityCalculator:
    """Build daily equity curves for proper Sharpe ratio and drawdown calculations"""
    
    def __init__(self, lot_tracker: LotTracker, price_oracle: PriceOracle, db_path: str):
        self.lot_tracker = lot_tracker
        self.price_oracle = price_oracle
        self.db_path = db_path
    
    def build_daily_equity_curve(self, wallet_address: str, start_date: date, end_date: date) -> List[Dict]:
        """Build daily portfolio value timeline for wallet"""
        equity_curve = []
        current_date = start_date
        
        while current_date <= end_date:
            portfolio_value = self.calculate_portfolio_value_at_date(wallet_address, current_date)
            realized_pnl = self.get_realized_pnl_to_date(wallet_address, current_date)
            total_invested = self.get_total_invested_to_date(wallet_address, current_date)
            
            equity_point = {
                'date': current_date,
                'portfolio_value_usd': portfolio_value,
                'realized_pnl': realized_pnl,
                'unrealized_pnl': portfolio_value - total_invested,
                'total_invested': total_invested
            }
            
            equity_curve.append(equity_point)
            self.save_equity_snapshot(wallet_address, equity_point)
            
            current_date += timedelta(days=1)
        
        return equity_curve
    
    def calculate_portfolio_value_at_date(self, wallet_address: str, target_date: date) -> float:
        """Calculate total portfolio value at specific date"""
        total_value = 0
        
        # Get open lots at this date
        open_lots = self.get_open_lots_at_date(wallet_address, target_date)
        
        for token_address, lot in open_lots:
            # Get token price at this date
            # Use a representative block number for the date (approximate)
            block_number = self.estimate_block_at_date(target_date)
            token_price = self.price_oracle.get_price_at_block(token_address, block_number)
            
            if token_price and lot.remaining_amount > 0:
                lot_value = lot.remaining_amount * token_price
                total_value += lot_value
        
        return total_value
    
    def get_open_lots_at_date(self, wallet_address: str, target_date: date) -> List[Tuple[str, TradeLot]]:
        """Get all open lots for wallet at specific date"""
        # This is a simplified version - in practice, you'd need to reconstruct
        # the lot state at the target date from the database
        open_lots = []
        
        for token_address, lot in self.lot_tracker.open_lots[wallet_address]:
            if lot.entry_timestamp.date() <= target_date:
                open_lots.append((token_address, lot))
        
        return open_lots
    
    def get_realized_pnl_to_date(self, wallet_address: str, target_date: date) -> float:
        """Get total realized P&L up to specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(net_pnl_usd) FROM closed_trade_lots 
            WHERE wallet_address = ? AND DATE(exit_timestamp) <= ?
        """, (wallet_address, target_date))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result or 0
    
    def get_total_invested_to_date(self, wallet_address: str, target_date: date) -> float:
        """Get total amount invested up to specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(value_usd) FROM token_fills 
            WHERE wallet_address = ? AND direction = 'BUY' AND DATE(block_timestamp) <= ?
        """, (wallet_address, target_date))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result or 0
    
    def estimate_block_at_date(self, target_date: date) -> int:
        """Estimate block number for a given date (approximate)"""
        # Ethereum averages ~12 second block times
        # This is a rough approximation - for production, use a block timestamp API
        genesis_date = date(2015, 7, 30)  # Ethereum genesis
        days_since_genesis = (target_date - genesis_date).days
        estimated_block = int(days_since_genesis * 24 * 60 * 60 / 12)  # ~7200 blocks/day
        
        return max(1, estimated_block)
    
    def save_equity_snapshot(self, wallet_address: str, equity_point: Dict):
        """Save daily equity snapshot to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO daily_equity (
                    wallet_address, date, portfolio_value_usd, 
                    realized_pnl_usd, unrealized_pnl_usd, total_invested_usd
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                wallet_address, equity_point['date'], equity_point['portfolio_value_usd'],
                equity_point['realized_pnl'], equity_point['unrealized_pnl'], 
                equity_point['total_invested']
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error saving equity snapshot: {e}")
        finally:
            conn.close()
    
    def calculate_sharpe_ratio(self, equity_curve: List[Dict], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio from daily equity curve"""
        if len(equity_curve) < 2:
            return 0
        
        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(equity_curve)):
            prev_value = equity_curve[i-1]['portfolio_value_usd']
            curr_value = equity_curve[i]['portfolio_value_usd']
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                daily_returns.append(daily_return)
        
        if not daily_returns:
            return 0
        
        # Calculate metrics
        avg_daily_return = statistics.mean(daily_returns)
        daily_volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
        
        # Annualize
        annual_return = avg_daily_return * 365
        annual_volatility = daily_volatility * math.sqrt(365)
        
        if annual_volatility == 0:
            return 0
        
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
        return sharpe_ratio
    
    def calculate_max_drawdown(self, equity_curve: List[Dict]) -> float:
        """Calculate maximum drawdown from equity curve"""
        if len(equity_curve) < 2:
            return 0
        
        peak_value = equity_curve[0]['portfolio_value_usd']
        max_drawdown = 0
        
        for point in equity_curve[1:]:
            current_value = point['portfolio_value_usd']
            
            if current_value > peak_value:
                peak_value = current_value
            elif peak_value > 0:
                drawdown = (peak_value - current_value) / peak_value
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown * 100  # Return as percentage

class PerformanceCalculator:
    """Calculate comprehensive performance metrics from lots and equity curve"""
    
    def __init__(self, lot_tracker: LotTracker, equity_calculator: EquityCalculator, db_path: str):
        self.lot_tracker = lot_tracker
        self.equity_calculator = equity_calculator
        self.db_path = db_path
    
    def calculate_wallet_performance(self, wallet_address: str, timeframe_days: int = 90) -> Dict:
        """Calculate comprehensive performance metrics"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=timeframe_days)
        
        # Get completed trades in timeframe
        completed_trades = self.get_completed_trades(wallet_address, start_date, end_date)
        
        if not completed_trades:
            return self.empty_performance_metrics(wallet_address, timeframe_days)
        
        # Build equity curve
        equity_curve = self.equity_calculator.build_daily_equity_curve(
            wallet_address, start_date, end_date
        )
        
        # Calculate comprehensive metrics
        metrics = {
            'wallet_address': wallet_address,
            'timeframe_days': timeframe_days,
            'total_trades': len(completed_trades),
            
            # Return metrics
            'total_net_pnl_usd': sum(trade.net_pnl_usd for trade in completed_trades),
            'avg_roi_percent': statistics.mean([trade.roi_percent for trade in completed_trades]),
            'median_roi_percent': statistics.median([trade.roi_percent for trade in completed_trades]),
            
            # Win/Loss metrics
            'winning_trades': len([t for t in completed_trades if t.net_pnl_usd > 0]),
            'losing_trades': len([t for t in completed_trades if t.net_pnl_usd <= 0]),
            'win_rate_percent': len([t for t in completed_trades if t.net_pnl_usd > 0]) / len(completed_trades) * 100,
            
            # Risk metrics (from equity curve)
            'sharpe_ratio': self.equity_calculator.calculate_sharpe_ratio(equity_curve),
            'max_drawdown_percent': self.equity_calculator.calculate_max_drawdown(equity_curve),
            
            # Trading patterns
            'avg_hold_days': statistics.mean([trade.hold_duration_days for trade in completed_trades]),
            'best_trade_roi': max(trade.roi_percent for trade in completed_trades),
            'worst_trade_roi': min(trade.roi_percent for trade in completed_trades),
            
            # Volume metrics
            'total_volume_usd': sum(trade.entry_value_usd for trade in completed_trades),
            'avg_position_size_usd': statistics.mean([trade.entry_value_usd for trade in completed_trades]),
            
            # Gas efficiency
            'total_gas_cost_usd': sum(trade.entry_gas_cost_usd + trade.exit_gas_cost_usd for trade in completed_trades),
            'gas_as_percent_of_volume': self.calculate_gas_efficiency(completed_trades),
        }
        
        # Save metrics to database
        self.save_performance_metrics(metrics)
        
        return metrics
    
    def get_completed_trades(self, wallet_address: str, start_date: date, end_date: date) -> List[ClosedTradeLot]:
        """Get completed trades from database for timeframe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM closed_trade_lots 
            WHERE wallet_address = ? AND DATE(exit_timestamp) BETWEEN ? AND ?
            ORDER BY exit_timestamp
        """, (wallet_address, start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to ClosedTradeLot objects (simplified)
        trades = []
        for row in rows:
            trade = ClosedTradeLot(
                wallet_address=row[1],
                token_address=row[2], 
                token_symbol=row[3],
                trade_amount=float(row[4]),
                entry_price_usd=float(row[5]),
                exit_price_usd=float(row[6]),
                entry_timestamp=datetime.fromisoformat(row[7]),
                exit_timestamp=datetime.fromisoformat(row[8]),
                hold_duration_days=int(row[9]),
                entry_value_usd=float(row[10]),
                exit_value_usd=float(row[11]),
                entry_gas_cost_usd=float(row[12]),
                exit_gas_cost_usd=float(row[13]),
                gross_pnl_usd=float(row[14]),
                net_pnl_usd=float(row[15]),
                roi_percent=float(row[16]),
                entry_fill=None,  # Simplified for this query
                exit_fill=None,   # Simplified for this query
                id=row[0]
            )
            trades.append(trade)
        
        return trades
    
    def calculate_gas_efficiency(self, trades: List[ClosedTradeLot]) -> float:
        """Calculate gas cost as percentage of total volume"""
        total_gas = sum(trade.entry_gas_cost_usd + trade.exit_gas_cost_usd for trade in trades)
        total_volume = sum(trade.entry_value_usd for trade in trades)
        
        return (total_gas / total_volume * 100) if total_volume > 0 else 0
    
    def empty_performance_metrics(self, wallet_address: str, timeframe_days: int) -> Dict:
        """Return empty metrics when no trades found"""
        return {
            'wallet_address': wallet_address,
            'timeframe_days': timeframe_days,
            'total_trades': 0,
            'total_net_pnl_usd': 0,
            'avg_roi_percent': 0,
            'median_roi_percent': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate_percent': 0,
            'sharpe_ratio': 0,
            'max_drawdown_percent': 0,
            'avg_hold_days': 0,
            'best_trade_roi': 0,
            'worst_trade_roi': 0,
            'total_volume_usd': 0,
            'avg_position_size_usd': 0,
            'total_gas_cost_usd': 0,
            'gas_as_percent_of_volume': 0,
        }
    
    def save_performance_metrics(self, metrics: Dict):
        """Save performance metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO performance_metrics (
                    wallet_address, timeframe_days, total_trades, total_net_pnl_usd,
                    avg_roi_percent, median_roi_percent, win_rate_percent, 
                    sharpe_ratio, max_drawdown_percent, avg_hold_days,
                    total_volume_usd, gas_efficiency_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics['wallet_address'], metrics['timeframe_days'], metrics['total_trades'],
                metrics['total_net_pnl_usd'], metrics['avg_roi_percent'], metrics['median_roi_percent'],
                metrics['win_rate_percent'], metrics['sharpe_ratio'], metrics['max_drawdown_percent'],
                metrics['avg_hold_days'], metrics['total_volume_usd'], metrics['gas_as_percent_of_volume']
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error saving performance metrics: {e}")
        finally:
            conn.close()

class ROIScorer:
    """Main ROI scoring system that integrates all components"""
    
    def __init__(self, web3_provider: Web3, db_path: str):
        self.w3 = web3_provider
        self.db_path = db_path
        
        # Initialize all components
        self.price_oracle = PriceOracle(web3_provider)
        self.event_processor = EventProcessor(web3_provider, db_path, self.price_oracle)
        self.lot_tracker = LotTracker(db_path)
        self.equity_calculator = EquityCalculator(self.lot_tracker, self.price_oracle, db_path)
        self.performance_calculator = PerformanceCalculator(
            self.lot_tracker, self.equity_calculator, db_path
        )
        
        # Ensure database schema exists
        create_roi_tracking_schema(db_path)
    
    def process_wallet_transactions(self, wallet_address: str, tx_hashes: List[str]):
        """Process all transactions for a wallet to build complete trading history"""
        logger.info(f"Processing {len(tx_hashes)} transactions for wallet {wallet_address}")
        
        all_fills = []
        
        for i, tx_hash in enumerate(tx_hashes):
            if i % 10 == 0:
                logger.info(f"Processing transaction {i+1}/{len(tx_hashes)}")
            
            # Extract fills from transaction
            fills = self.event_processor.process_transaction_events(tx_hash)
            
            for fill in fills:
                # Save fill to database
                fill_id = self.event_processor.save_fill_to_db(fill)
                fill.id = fill_id
                
                # Process fill for lot tracking
                self.lot_tracker.process_fill(fill)
                
                all_fills.append(fill)
        
        logger.info(f"Processed {len(all_fills)} fills for wallet {wallet_address}")
        return all_fills
    
    def calculate_wallet_score(self, wallet_address: str, timeframe_days: int = 90) -> Dict:
        """Calculate comprehensive ROI-based score for wallet"""
        logger.info(f"Calculating ROI score for wallet {wallet_address}")
        
        # Get performance metrics
        metrics = self.performance_calculator.calculate_wallet_performance(
            wallet_address, timeframe_days
        )
        
        # Calculate composite score (0-100 scale)
        score_components = {
            'roi_score': self.score_roi(metrics['avg_roi_percent']),
            'volume_score': self.score_volume(metrics['total_volume_usd']),
            'consistency_score': self.score_consistency(metrics['win_rate_percent']),
            'risk_score': self.score_risk(metrics['sharpe_ratio'], metrics['max_drawdown_percent']),
            'activity_score': self.score_activity(metrics['total_trades'], timeframe_days),
            'efficiency_score': self.score_efficiency(metrics['gas_as_percent_of_volume'])
        }
        
        # Weighted composite score
        weights = {
            'roi_score': 0.30,
            'volume_score': 0.20,
            'consistency_score': 0.20,
            'risk_score': 0.15,
            'activity_score': 0.10,
            'efficiency_score': 0.05
        }
        
        composite_score = sum(
            score_components[component] * weights[component] 
            for component in score_components
        )
        
        return {
            'wallet_address': wallet_address,
            'composite_score': round(composite_score, 2),
            'score_components': score_components,
            'raw_metrics': metrics,
            'calculated_at': datetime.now().isoformat()
        }
    
    def score_roi(self, avg_roi_percent: float) -> float:
        """Score based on average ROI (0-100)"""
        if avg_roi_percent <= 0:
            return 0
        elif avg_roi_percent >= 100:
            return 100
        else:
            return min(100, avg_roi_percent)
    
    def score_volume(self, total_volume_usd: float) -> float:
        """Score based on trading volume (0-100)"""
        if total_volume_usd >= 1000000:  # $1M+
            return 100
        elif total_volume_usd >= 100000:  # $100K+
            return 80
        elif total_volume_usd >= 10000:   # $10K+
            return 60
        elif total_volume_usd >= 1000:    # $1K+
            return 40
        else:
            return 20
    
    def score_consistency(self, win_rate_percent: float) -> float:
        """Score based on win rate (0-100)"""
        return min(100, win_rate_percent * 1.25)  # 80% win rate = 100 points
    
    def score_risk(self, sharpe_ratio: float, max_drawdown_percent: float) -> float:
        """Score based on risk-adjusted returns (0-100)"""
        sharpe_score = min(100, max(0, sharpe_ratio * 20))  # Sharpe of 5 = 100 points
        drawdown_score = max(0, 100 - max_drawdown_percent * 2)  # 50% drawdown = 0 points
        
        return (sharpe_score + drawdown_score) / 2
    
    def score_activity(self, total_trades: int, timeframe_days: int) -> float:
        """Score based on trading activity (0-100)"""
        trades_per_day = total_trades / timeframe_days
        
        if trades_per_day >= 1:
            return 100
        elif trades_per_day >= 0.5:
            return 80
        elif trades_per_day >= 0.1:
            return 60
        else:
            return 40
    
    def score_efficiency(self, gas_percent: float) -> float:
        """Score based on gas efficiency (0-100)"""
        if gas_percent <= 1:
            return 100
        elif gas_percent <= 2:
            return 80
        elif gas_percent <= 5:
            return 60
        else:
            return 40

if __name__ == "__main__":
    # Example usage
    db_path = "roi_tracking.db"
    create_roi_tracking_schema(db_path)
    print("ROI tracking database schema created successfully!")
    
    # Example initialization (requires Web3 provider)
    # w3 = Web3(Web3.HTTPProvider('YOUR_ETH_RPC_URL'))
    # roi_scorer = ROIScorer(w3, db_path)
    # score = roi_scorer.calculate_wallet_score('0x...wallet_address...')