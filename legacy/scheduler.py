import schedule
import time
from whale_scanner import WhaleScanner
from datetime import datetime

def run_whale_scan():
    """Run whale scanner and log the results"""
    print(f"\n🐋 ETHhab scan starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        scanner = WhaleScanner()
        scanner.run_scan()
        print("✅ Scan completed successfully!")
    except Exception as e:
        print(f"❌ Scan failed: {e}")

def main():
    """Main scheduler loop"""
    print("🐋 ETHhab Scheduler Started!")
    print("📅 Scheduled whale scans every hour")
    print("⏰ Next scan will run at the top of the hour")
    print("Press Ctrl+C to stop\n")
    
    # Schedule whale scans every hour
    schedule.every().hour.at(":00").do(run_whale_scan)
    
    # Run an initial scan
    print("🚀 Running initial whale scan...")
    run_whale_scan()
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n🛑 ETHhab scheduler stopped by user")
            break
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()