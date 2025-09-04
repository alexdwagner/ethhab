-- Smart Money Discovery Database Schema

-- DEX Router Registry
CREATE TABLE IF NOT EXISTS dex_routers (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- CEX Address Registry
CREATE TABLE IF NOT EXISTS cex_addresses (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) UNIQUE NOT NULL,
    exchange_name VARCHAR(100) NOT NULL,
    address_type VARCHAR(20), -- 'hot_wallet', 'cold_wallet'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Contract Registry (for exclusions)
CREATE TABLE IF NOT EXISTS known_contracts (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) UNIQUE NOT NULL,
    contract_type VARCHAR(50), -- 'dex', 'bridge', 'token', 'staking'
    name VARCHAR(100),
    should_exclude BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Address Activity Tracking
CREATE TABLE IF NOT EXISTS address_activity (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) UNIQUE NOT NULL,
    dex_swap_count INTEGER DEFAULT 0,
    unique_protocols INTEGER DEFAULT 0,
    total_gas_spent_eth DECIMAL(18,6) DEFAULT 0,
    first_seen_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    withdrew_from_cex BOOLEAN DEFAULT false,
    uses_defi BOOLEAN DEFAULT false,
    is_contract BOOLEAN DEFAULT false,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- DEX Interactions Log
CREATE TABLE IF NOT EXISTS dex_interactions (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) NOT NULL,
    router_address VARCHAR(42) NOT NULL,
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    block_number BIGINT,
    timestamp TIMESTAMP,
    gas_spent_eth DECIMAL(18,6),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Smart Money Candidates
CREATE TABLE IF NOT EXISTS smart_money_candidates (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) UNIQUE NOT NULL,
    status VARCHAR(20), -- 'candidate', 'scored', 'watchlist'
    dex_swaps_90d INTEGER DEFAULT 0,
    volume_90d_usd DECIMAL(18,2),
    sharpe_ratio DECIMAL(10,4),
    win_rate DECIMAL(5,2),
    confidence_score DECIMAL(5,2), -- % of trades with USD pricing
    qualifies_smart_money BOOLEAN DEFAULT false,
    last_evaluated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_candidates_status ON smart_money_candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_sharpe ON smart_money_candidates(sharpe_ratio DESC);
CREATE INDEX IF NOT EXISTS idx_activity_swaps ON address_activity(dex_swap_count DESC);
CREATE INDEX IF NOT EXISTS idx_activity_last ON address_activity(last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_dex_interactions_address ON dex_interactions(address);
CREATE INDEX IF NOT EXISTS idx_dex_interactions_timestamp ON dex_interactions(timestamp);
