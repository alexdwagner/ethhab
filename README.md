# ETHhab 🐋

*"Call me ETHhab"* - Like Captain Ahab, but hunting Ethereum whales!

A free, local whale tracking system for Ethereum that monitors large ETH holders and their transaction patterns.

## Features

- 🐋 Track top 100+ Ethereum whales
- 📊 Real-time balance monitoring
- 🚨 Smart alerts for large transactions and patterns
- 📈 Pattern analysis (accumulation/distribution)
- 🖥️ Web dashboard with charts
- 💰 100% free using public APIs

## Quick Start

### 1. Setup Environment

```bash
# Clone and enter directory
cd whale-tracker

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Get Free API Keys

**Alchemy (Required)**
1. Go to https://www.alchemy.com/
2. Sign up for free account
3. Create new app (Ethereum Mainnet)
4. Copy API key to `.env`

**Etherscan (Required)**
1. Go to https://etherscan.io/apis
2. Sign up for free account
3. Create API key
4. Copy API key to `.env`

### 3. Run First Scan

```bash
python whale_scanner.py
```

### 4. Start Dashboard

```bash
streamlit run dashboard.py
```

Open http://localhost:8501 to view your whale tracker!

## How It Works

1. **Whale Detection**: Scans addresses with 1000+ ETH
2. **Pattern Analysis**: Tracks accumulation/distribution patterns
3. **Alert System**: Notifications for large transactions (>100 ETH)
4. **Dashboard**: Visual tracking of whale activities

## Free Tier Limits

- **Alchemy**: 3.8M requests/month
- **Etherscan**: 100K requests/day
- **Tracking Capacity**: ~100 whales with hourly updates

## File Structure

```
whale-tracker/
├── database.py         # Database models and operations
├── whale_scanner.py    # Main scanning logic
├── dashboard.py        # Streamlit web interface
├── scheduler.py        # Automated scanning
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
└── README.md          # This file
```

## Usage Tips

- Run scanner manually first to build initial database
- Use scheduler.py for automated hourly scans
- Check dashboard for whale activities and alerts
- Monitor free API usage to stay within limits

## Whale Tiers

- **Mini Whale**: 100-1,000 ETH
- **Large Whale**: 1,000-10,000 ETH  
- **Mega Whale**: 10,000+ ETH
- **Institutional**: 100,000+ ETH

## Contributing

This is a personal project but feel free to fork and customize for your needs!