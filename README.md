# Whale Tracker 🐋

Professional-grade Ethereum whale tracking platform with ROI scoring and real-time analytics.

## Features

- 🐋 **Advanced Whale Detection**: Track 1000+ Ethereum whales with smart categorization
- 📊 **ROI Scoring System**: Composite scoring based on performance metrics
- 🏗️ **Supabase Integration**: PostgreSQL database with real-time capabilities
- 📱 **Mobile-First Dashboard**: NextJS + Tailwind responsive design
- 📈 **Real-time Updates**: Live whale monitoring with auto-refresh
- 🔄 **Full-Stack Architecture**: Python backend + React frontend
- 🌐 **REST API**: Programmatic access to whale data
- 💰 **Free & Open Source**: No subscription fees

## Tech Stack

**Frontend**
- NextJS 15 (App Router)
- TypeScript
- Tailwind CSS
- Real-time data fetching

**Backend** 
- Python 3.8+
- Supabase PostgreSQL
- RESTful API design
- Etherscan/Alchemy APIs

## Quick Start

**⚠️ Note: This is a Supabase-first application. SQLite is not supported.**

### 1. Setup Supabase Database (Required)

1. **Create Supabase Project**
   - Go to https://supabase.com
   - Sign up and create new project (free tier: 500MB)
   - Wait for database to initialize (~2 minutes)

2. **Get Database Credentials**
   - Go to Project Settings → API
   - Copy Project URL and `anon` `public` key

### 2. Environment Configuration

```bash
# Clone repository
git clone <your-repo-url>
cd whale-tracker

# Install dependencies  
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials
```

### 3. Database Setup

```bash
# Initialize Supabase schema
python scripts/setup_supabase.py
```

### 4. Get API Keys

**Alchemy (Required)**
- Visit https://www.alchemy.com/
- Create free account → New App (Ethereum Mainnet)
- Add API key to `.env`

**Etherscan (Required)** 
- Visit https://etherscan.io/apis
- Create free account → Generate API key
- Add API key to `.env`

### 5. Launch Application

**Option A: Full Stack (Recommended)**
```bash
# Terminal 1: Start Python backend (default 8080)
python app.py --port 8080

# Terminal 2: Start NextJS frontend
cd frontend
# Optional: set backend URL for the frontend
echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:8080" > .env.local
npm run dev
```

Visit http://localhost:3000 for the modern dashboard!

**Option B: API Only**
```bash
python app.py
```
Visit http://localhost:8080/api/whales for JSON data

## Deployment

### Backend (Render)

We include a `render.yaml` Blueprint for hosting the Python backend and a daily refresh cron.

Steps
- Create a new Render Blueprint from this repo (Render → New + → Blueprint).
- In the `whale-backend` service, set env vars:
  - `SUPABASE_URL` (Supabase → Settings → API)
  - `SUPABASE_SERVICE_ROLE_KEY` (service role key)
  - `ETH_RPC_URL` (Alchemy RPC URL) or set `ALCHEMY_API_KEY`
  - `ETHERSCAN_API_KEY` (optional)
  - `COINGECKO_API_KEY` (optional)
  - `ADMIN_API_TOKEN` (random string to protect `POST /admin/refresh`)
  - `DEV_DEBUG=0`
- The cron service `whale-refresh-cron` will call `https://<backend>/admin/refresh` daily.

### Frontend (Vercel)

- Create a Vercel project from `/frontend`.
- Set `NEXT_PUBLIC_BACKEND_URL=https://<your-render-backend-host>`.
- Deploy and visit `/smart-money`.

### Manual Admin Refresh (Protected)

Trigger a refresh job:

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"top":100,"hours":720,"price_days":90,"metrics_days":90,"activity_days":90,"time_budget":240}' \
  https://<your-render-backend>/admin/refresh
```

Job logs are stored in `job_logs`.

## Architecture

### Modern Full-Stack Architecture
```
whale-tracker/
├── frontend/             # NextJS + Tailwind frontend
│   ├── src/app/         # App router pages
│   ├── components/      # Reusable UI components
│   └── public/          # Static assets
├── src/                 # Python backend
│   ├── services/        # Business logic layer
│   │   ├── whale_service.py
│   │   └── roi_service.py
│   ├── data/           # Data access layer
│   │   ├── supabase_client.py
│   │   └── whale_repository.py
│   └── api/            # REST API layer
│       └── handlers.py
├── config/             # Configuration management
├── scripts/           # Setup and utility scripts
├── legacy/            # Legacy code (migrated)
└── tests/             # Test suite
```

### Database Schema (PostgreSQL)
- **whales**: Core whale data with address, balance, entity type
- **whale_roi_scores**: Composite ROI scoring metrics
- **whale_transactions**: Detailed transaction tracking

## API Endpoints

- `GET /` - Dashboard UI
- `GET /api/whales` - Whale data with ROI scores
- `GET /api/stats` - Database statistics
- `GET /api/scan` - Trigger whale scan
- `GET /health` - Read-only health check (public safe)
- `GET /health/db-write` - Dev-only write health check (token-gated)

- `GET /smart-money` - Smart Money leaderboard (fallback aggregation)
  - Query params: `limit` (default 50), `min_swaps` (default 10), `active_days` (default 30)
  - Example: `http://localhost:8080/smart-money?limit=50&min_swaps=10&active_days=30`

### Populate Smart Money List

Use the CLI to seed config and run bounded discovery without hanging:

```bash
# Seed DEX routers / CEX addresses from JSON templates
python scripts/smart_money_cli.py seed --routers sample_dex_routers.json --cex sample_cex_addresses.json

# Run discovery with guardrails
python scripts/smart_money_cli.py discover \
  --limit 100 \
  --hours 24 \
  --max-routers 5 \
  --time-budget 60

# Offline (DB-only) mode when network is constrained
python scripts/smart_money_cli.py discover --offline --limit 100
```

You can also tune via environment variables in `.env`:
`SMART_MONEY_MAX_ROUTERS_PER_RUN`, `SMART_MONEY_DISCOVERY_TIME_BUDGET_SEC`, `SMART_MONEY_REQUEST_TIMEOUT_SEC`, `SMART_MONEY_DISABLE_NETWORK`.

Dev write-check usage
```bash
# Requires header Authorization: Bearer whale-dev-2024
curl -H "Authorization: Bearer whale-dev-2024" http://localhost:8080/health/db-write
```
Returns JSON with write/cleanup status and response time; rate-limited by a 60s cooldown. Do not expose in production.

## ROI Scoring System

Composite score calculated from:
- **ROI Score (30%)**: Historical return performance
- **Volume Score (20%)**: Trading volume analysis
- **Consistency Score (20%)**: Performance consistency
- **Risk Score (15%)**: Risk-adjusted returns
- **Activity Score (10%)**: Transaction frequency
- **Efficiency Score (5%)**: Gas optimization

## Development

### Local Development
```bash
# Run tests
python tests/test_basic.py

# Development server
python app.py --port 8080

# Check configuration
python app.py --config
```

### Environment Variables
```env
# Supabase (Required)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key

# API Keys (Required)
ETHERSCAN_API_KEY=your_key
ALCHEMY_API_KEY=your_key

# Application Settings
HOST=localhost
PORT=8080
WHALE_THRESHOLD=1000
```

## Scaling Notes

- **Supabase Free Tier**: 500MB storage, 2M API requests/month
- **API Rate Limits**: Etherscan 5 req/sec, Alchemy varies by plan
- **Recommended**: Start with 50-100 whales, scale based on usage

## Why Supabase-Only?

We eliminated SQLite to provide a **modern, scalable architecture**:

✅ **Real-time Updates**: Live whale monitoring  
✅ **Proper Relationships**: Foreign keys, constraints, transactions  
✅ **Auto-scaling**: Handle thousands of whales  
✅ **Zero Maintenance**: Managed backups, updates  
✅ **Team Collaboration**: Shared dev/staging/prod environments  
✅ **Edge Functions**: Future extensibility  

**Legacy Migration**: Old SQLite files are in `/legacy/databases/` for reference.
