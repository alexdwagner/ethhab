-- WHALE TRACKER - PRODUCTION SCHEMA
-- Aligned with roadmap phases 1-3 and ROI algorithm v2

-- =================================================================
-- CORE USER MANAGEMENT (Phase 1: Web Platform)
-- =================================================================

-- Users and authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255),
    subscription_tier VARCHAR(20) DEFAULT 'free', -- 'free', 'pro', 'premium'
    subscription_expires_at TIMESTAMPTZ,
    email_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true
);

-- User whale follows (Phase 1: Core Feature)
CREATE TABLE IF NOT EXISTS user_whale_follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    whale_address VARCHAR(42) NOT NULL,
    nickname VARCHAR(100),
    alert_threshold_usd DECIMAL(12,2) DEFAULT 10000, -- Alert for transactions above this
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, whale_address)
);

-- User alert preferences  
CREATE TABLE IF NOT EXISTS user_alert_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email_alerts BOOLEAN DEFAULT true,
    push_notifications BOOLEAN DEFAULT true,
    telegram_chat_id VARCHAR(50),
    min_transaction_usd DECIMAL(12,2) DEFAULT 50000,
    alert_types TEXT[] DEFAULT '{"large_transaction", "whale_awakening", "new_position"}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- =================================================================
-- ENHANCED WHALE TRACKING (Improved from Legacy)
-- =================================================================

-- Core whale registry (enhanced from legacy)
CREATE TABLE IF NOT EXISTS whales (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) UNIQUE NOT NULL,
    label VARCHAR(255),
    balance_eth DECIMAL(20,8) DEFAULT 0,
    balance_usd DECIMAL(20,2) DEFAULT 0,
    max_balance_eth DECIMAL(20,8) DEFAULT 0,
    total_volume_eth DECIMAL(20,8) DEFAULT 0,
    transaction_count INTEGER DEFAULT 0,
    
    -- Enhanced categorization
    entity_type VARCHAR(100), -- 'Individual', 'Exchange', 'Institution', 'Protocol', 'Bridge'
    category VARCHAR(100), -- 'CEX Hot Wallet', 'DeFi Whale', 'NFT Collector', etc.
    whale_tier VARCHAR(20), -- 'Mini', 'Large', 'Mega', 'Institutional'
    smart_money_category VARCHAR(50), -- 'Smart Money', 'Copy Trader', 'MEV Bot', 'Arbitrageur'
    
    -- Activity tracking
    is_active BOOLEAN DEFAULT true,
    dormant_since TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Social/Following metrics
    follower_count INTEGER DEFAULT 0,
    copy_trader_count INTEGER DEFAULT 0,
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =================================================================
-- EVENT-SOURCED ROI SYSTEM (Algorithm v2)
-- =================================================================

-- Raw blockchain fills (event-sourced core)
CREATE TABLE IF NOT EXISTS token_fills (
    id SERIAL PRIMARY KEY,
    whale_address VARCHAR(42) NOT NULL,
    token_address VARCHAR(42) NOT NULL,
    token_symbol VARCHAR(20) NOT NULL,
    token_decimals INTEGER NOT NULL,
    direction VARCHAR(4) NOT NULL, -- 'BUY', 'SELL'
    amount DECIMAL(36,18) NOT NULL,
    price_usd DECIMAL(18,8),
    value_usd DECIMAL(18,2),
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    transaction_hash VARCHAR(66) NOT NULL,
    log_index INTEGER NOT NULL,
    gas_cost_usd DECIMAL(18,2),
    counterparty VARCHAR(42),
    dex_name VARCHAR(50), -- 'Uniswap V3', 'Curve', '1inch'
    pool_address VARCHAR(42),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(transaction_hash, log_index)
);

-- Closed trade lots (FIFO accounting for accurate P&L)
CREATE TABLE IF NOT EXISTS closed_trade_lots (
    id SERIAL PRIMARY KEY,
    whale_address VARCHAR(42) NOT NULL,
    token_address VARCHAR(42) NOT NULL,
    token_symbol VARCHAR(20) NOT NULL,
    trade_amount DECIMAL(36,18) NOT NULL,
    entry_price_usd DECIMAL(18,8) NOT NULL,
    exit_price_usd DECIMAL(18,8) NOT NULL,
    entry_timestamp TIMESTAMPTZ NOT NULL,
    exit_timestamp TIMESTAMPTZ NOT NULL,
    hold_duration_days INTEGER NOT NULL,
    entry_value_usd DECIMAL(18,2) NOT NULL,
    exit_value_usd DECIMAL(18,2) NOT NULL,
    entry_gas_cost_usd DECIMAL(18,2) NOT NULL,
    exit_gas_cost_usd DECIMAL(18,2) NOT NULL,
    gross_pnl_usd DECIMAL(18,2) NOT NULL,
    net_pnl_usd DECIMAL(18,2) NOT NULL,
    roi_percent DECIMAL(10,4) NOT NULL,
    entry_fill_id INTEGER REFERENCES token_fills(id),
    exit_fill_id INTEGER REFERENCES token_fills(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily equity snapshots (for Sharpe ratio, drawdown)
CREATE TABLE IF NOT EXISTS daily_equity_snapshots (
    id SERIAL PRIMARY KEY,
    whale_address VARCHAR(42) NOT NULL,
    snapshot_date DATE NOT NULL,
    portfolio_value_usd DECIMAL(18,2) NOT NULL,
    realized_pnl_usd DECIMAL(18,2) NOT NULL,
    unrealized_pnl_usd DECIMAL(18,2) NOT NULL,
    total_invested_usd DECIMAL(18,2) NOT NULL,
    active_positions INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(whale_address, snapshot_date)
);

-- Comprehensive whale scoring (enhanced from current)
CREATE TABLE IF NOT EXISTS whale_roi_scores (
    id SERIAL PRIMARY KEY,
    whale_id INTEGER REFERENCES whales(id) ON DELETE CASCADE,
    whale_address VARCHAR(42) NOT NULL,
    
    -- Core composite score
    composite_score DECIMAL(5,2) DEFAULT 0,
    
    -- Component scores (0-100)
    roi_score DECIMAL(5,2) DEFAULT 0,
    volume_score DECIMAL(5,2) DEFAULT 0,
    consistency_score DECIMAL(5,2) DEFAULT 0,
    risk_score DECIMAL(5,2) DEFAULT 0,
    activity_score DECIMAL(5,2) DEFAULT 0,
    efficiency_score DECIMAL(5,2) DEFAULT 0,
    
    -- Trading metrics
    total_trades INTEGER DEFAULT 0,
    avg_roi_percent DECIMAL(10,4) DEFAULT 0,
    median_roi_percent DECIMAL(10,4) DEFAULT 0,
    win_rate_percent DECIMAL(10,4) DEFAULT 0,
    total_volume_usd DECIMAL(20,2) DEFAULT 0,
    
    -- Risk metrics (from equity curve)
    sharpe_ratio DECIMAL(6,3) DEFAULT 0,
    max_drawdown_percent DECIMAL(6,2) DEFAULT 0,
    volatility_percent DECIMAL(6,2) DEFAULT 0,
    
    -- Pattern metrics
    avg_hold_days DECIMAL(8,2) DEFAULT 0,
    best_trade_roi DECIMAL(10,4) DEFAULT 0,
    worst_trade_roi DECIMAL(10,4) DEFAULT 0,
    
    -- Gas efficiency
    avg_gas_per_trade_usd DECIMAL(10,2) DEFAULT 0,
    gas_efficiency_score DECIMAL(5,2) DEFAULT 0,
    
    -- Timeframe
    calculation_period_days INTEGER DEFAULT 90,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(whale_address)
);

-- =================================================================
-- ADVANCED ANALYTICS (Phases 2-3)
-- =================================================================

-- Whale behavior patterns (AI/ML features)
CREATE TABLE IF NOT EXISTS whale_behavior_patterns (
    id SERIAL PRIMARY KEY,
    whale_address VARCHAR(42) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL, -- 'accumulation', 'distribution', 'rotation', 'arbitrage'
    confidence_score DECIMAL(5,2) NOT NULL,
    tokens_involved TEXT[], -- Array of token addresses
    pattern_start_date TIMESTAMPTZ NOT NULL,
    pattern_end_date TIMESTAMPTZ,
    description TEXT,
    ai_model_version VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market correlation tracking
CREATE TABLE IF NOT EXISTS whale_market_correlations (
    id SERIAL PRIMARY KEY,
    whale_address VARCHAR(42) NOT NULL,
    token_address VARCHAR(42) NOT NULL,
    correlation_type VARCHAR(30), -- 'price_impact', 'timing_lead', 'volume_correlation'
    correlation_coefficient DECIMAL(6,4), -- -1 to 1
    confidence_interval DECIMAL(5,2),
    sample_size INTEGER,
    calculation_period_days INTEGER,
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Whale social network analysis
CREATE TABLE IF NOT EXISTS whale_copy_network (
    id SERIAL PRIMARY KEY,
    leader_address VARCHAR(42) NOT NULL,
    follower_address VARCHAR(42) NOT NULL,
    copy_accuracy_percent DECIMAL(5,2),
    time_lag_minutes INTEGER, -- How quickly follower copies leader
    copy_volume_ratio DECIMAL(8,4), -- Follower volume / Leader volume
    relationship_start_date TIMESTAMPTZ,
    relationship_confidence DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(leader_address, follower_address)
);

-- =================================================================
-- ENHANCED TRANSACTION TRACKING
-- =================================================================

-- Comprehensive transaction log (enhanced from legacy)
CREATE TABLE IF NOT EXISTS whale_transactions (
    id SERIAL PRIMARY KEY,
    hash VARCHAR(66) UNIQUE NOT NULL,
    whale_id INTEGER REFERENCES whales(id) ON DELETE CASCADE,
    whale_address VARCHAR(42) NOT NULL,
    from_address VARCHAR(42) NOT NULL,
    to_address VARCHAR(42) NOT NULL,
    
    -- Value tracking
    amount_eth DECIMAL(20,8) NOT NULL,
    amount_usd DECIMAL(20,2),
    amount_wei DECIMAL(30,0),
    
    -- Gas tracking
    gas_price_gwei DECIMAL(20,8),
    gas_used BIGINT,
    transaction_fee_eth DECIMAL(20,8),
    transaction_fee_usd DECIMAL(12,2),
    
    -- Block data
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    
    -- Transaction categorization
    transaction_type VARCHAR(50), -- 'transfer', 'swap', 'deposit', 'withdraw', 'mint', 'burn'
    sub_type VARCHAR(50), -- 'dex_trade', 'lending', 'staking', 'nft_purchase'
    
    -- Token data (for ERC20 transfers)
    token_address VARCHAR(42),
    token_symbol VARCHAR(20),
    token_amount DECIMAL(36,18),
    
    -- DEX data
    dex_name VARCHAR(50),
    pool_address VARCHAR(42),
    swap_path TEXT[], -- Array of token addresses in swap path
    
    -- Impact metrics
    price_impact_percent DECIMAL(8,4),
    slippage_percent DECIMAL(8,4),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =================================================================
-- REAL-TIME ALERT SYSTEM
-- =================================================================

-- User alerts (enhanced from legacy)
CREATE TABLE IF NOT EXISTS user_alerts (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    whale_address VARCHAR(42) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    
    -- Transaction context
    transaction_hash VARCHAR(66),
    amount_eth DECIMAL(20,8),
    amount_usd DECIMAL(20,2),
    token_symbol VARCHAR(20),
    
    -- Alert metadata
    priority VARCHAR(10) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    
    -- Delivery tracking
    email_sent BOOLEAN DEFAULT false,
    push_sent BOOLEAN DEFAULT false,
    telegram_sent BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Global whale alerts (for public feed)
CREATE TABLE IF NOT EXISTS global_whale_alerts (
    id SERIAL PRIMARY KEY,
    whale_address VARCHAR(42) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- 'large_transaction', 'whale_awakening', 'new_pattern'
    severity VARCHAR(10) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    title VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Context data
    transaction_hash VARCHAR(66),
    amount_usd DECIMAL(20,2),
    token_involved VARCHAR(20),
    
    -- Engagement metrics
    view_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    
    is_featured BOOLEAN DEFAULT false,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =================================================================
-- PERFORMANCE INDEXES
-- =================================================================

-- User management indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_tier, subscription_expires_at);
CREATE INDEX IF NOT EXISTS idx_user_follows_user_id ON user_whale_follows(user_id);
CREATE INDEX IF NOT EXISTS idx_user_follows_whale ON user_whale_follows(whale_address);

-- Whale tracking indexes
CREATE INDEX IF NOT EXISTS idx_whales_address ON whales(address);
CREATE INDEX IF NOT EXISTS idx_whales_balance_eth ON whales(balance_eth DESC);
CREATE INDEX IF NOT EXISTS idx_whales_tier ON whales(whale_tier);
CREATE INDEX IF NOT EXISTS idx_whales_entity_type ON whales(entity_type);
CREATE INDEX IF NOT EXISTS idx_whales_smart_money ON whales(smart_money_category);
CREATE INDEX IF NOT EXISTS idx_whales_last_activity ON whales(last_activity_at DESC);

-- ROI system indexes
CREATE INDEX IF NOT EXISTS idx_token_fills_whale ON token_fills(whale_address, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_token_fills_token ON token_fills(token_address, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_token_fills_block ON token_fills(block_number DESC);
CREATE INDEX IF NOT EXISTS idx_closed_lots_whale ON closed_trade_lots(whale_address, exit_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_closed_lots_roi ON closed_trade_lots(roi_percent DESC);
CREATE INDEX IF NOT EXISTS idx_daily_equity_whale ON daily_equity_snapshots(whale_address, snapshot_date DESC);

-- ROI scores indexes
CREATE INDEX IF NOT EXISTS idx_roi_composite ON whale_roi_scores(composite_score DESC);
CREATE INDEX IF NOT EXISTS idx_roi_sharpe ON whale_roi_scores(sharpe_ratio DESC);
CREATE INDEX IF NOT EXISTS idx_roi_volume ON whale_roi_scores(total_volume_usd DESC);
CREATE INDEX IF NOT EXISTS idx_roi_updated ON whale_roi_scores(updated_at DESC);

-- Transaction indexes
CREATE INDEX IF NOT EXISTS idx_tx_whale_address ON whale_transactions(whale_address, block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tx_hash ON whale_transactions(hash);
CREATE INDEX IF NOT EXISTS idx_tx_block ON whale_transactions(block_number DESC);
CREATE INDEX IF NOT EXISTS idx_tx_amount ON whale_transactions(amount_usd DESC);
CREATE INDEX IF NOT EXISTS idx_tx_type ON whale_transactions(transaction_type, sub_type);
CREATE INDEX IF NOT EXISTS idx_tx_token ON whale_transactions(token_address, block_timestamp DESC);

-- Alert indexes
CREATE INDEX IF NOT EXISTS idx_alerts_user ON user_alerts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_whale ON user_alerts(whale_address, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON user_alerts(user_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_global_alerts_featured ON global_whale_alerts(is_featured, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_global_alerts_severity ON global_whale_alerts(severity, created_at DESC);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_patterns_whale ON whale_behavior_patterns(whale_address, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON whale_behavior_patterns(pattern_type, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_correlations_whale ON whale_market_correlations(whale_address, calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_copy_network_leader ON whale_copy_network(leader_address, copy_accuracy_percent DESC);

-- =================================================================
-- ROW LEVEL SECURITY (Optional - for multi-tenant)
-- =================================================================

-- Enable RLS on user-specific tables
-- ALTER TABLE user_whale_follows ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_alert_settings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_alerts ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (users can only see their own data)
-- CREATE POLICY user_follows_policy ON user_whale_follows
--     USING (user_id = auth.uid());

-- =================================================================
-- ANALYTICS VIEWS (Performance optimization)
-- =================================================================

-- Top performing whales view
CREATE OR REPLACE VIEW top_whales_performance AS
SELECT 
    w.address,
    w.label,
    w.whale_tier,
    w.entity_type,
    w.smart_money_category,
    w.balance_eth,
    w.balance_usd,
    r.composite_score,
    r.roi_score,
    r.sharpe_ratio,
    r.total_trades,
    r.win_rate_percent,
    r.total_volume_usd,
    w.follower_count,
    w.last_activity_at
FROM whales w
LEFT JOIN whale_roi_scores r ON w.address = r.whale_address
WHERE w.is_active = true
ORDER BY r.composite_score DESC;

-- Recent whale activity view  
CREATE OR REPLACE VIEW recent_whale_activity AS
SELECT 
    wt.whale_address,
    w.label,
    wt.transaction_type,
    wt.amount_usd,
    wt.token_symbol,
    wt.block_timestamp,
    wt.hash
FROM whale_transactions wt
JOIN whales w ON wt.whale_address = w.address
WHERE wt.block_timestamp > NOW() - INTERVAL '24 hours'
AND wt.amount_usd > 10000
ORDER BY wt.block_timestamp DESC;