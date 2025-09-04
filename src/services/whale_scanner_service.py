#!/usr/bin/env python3
"""
Whale Scanner Background Service
Enhanced background scanning service for whale address monitoring
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ..data.whale_repository import whale_repository
from .whale_service import WhaleService
from .roi_service import ROIService

class WhaleScannerService:
    """Background service for scanning whale addresses"""
    
    def __init__(self):
        self.whale_service = WhaleService()
        self.roi_service = ROIService() if 'ROIService' in globals() else None
        self.whale_repo = whale_repository
        self.is_running = False
        self.scan_thread = None
        self.last_scan_time = None
        self.scan_interval_hours = 1  # Default: scan every hour
        
        if not self.whale_repo:
            raise ValueError("Whale repository not available - check Supabase configuration")
    
    def scan_whale_batch(self, addresses: List[str], batch_name: str = "batch") -> Dict:
        """Scan a batch of whale addresses and store results"""
        print(f"🔍 Starting {batch_name} scan ({len(addresses)} addresses)")
        start_time = time.time()
        
        successful_scans = 0
        failed_scans = 0
        total_eth = 0
        
        for i, address in enumerate(addresses):
            try:
                print(f"📊 Scanning {i+1}/{len(addresses)}: {address[:10]}...")
                
                # Get whale info with fresh balance data
                whale_info = self.whale_service.get_whale_info(address)
                
                if whale_info and whale_info.get('balance_eth', 0) > 0:
                    # Save to database
                    success = self.whale_repo.save_whale(
                        address=whale_info['address'],
                        label=whale_info['display_name'],
                        balance_eth=whale_info['balance_eth'],
                        entity_type=whale_info.get('entity_type'),
                        category=whale_info.get('category')
                    )
                    
                    if success:
                        successful_scans += 1
                        total_eth += whale_info['balance_eth']
                        
                        # Generate ROI score if service is available
                        if self.roi_service:
                            try:
                                roi_data = self.roi_service.calculate_roi_score(address)
                                if roi_data:
                                    self.whale_repo.save_roi_score(address, **roi_data)
                            except Exception as e:
                                print(f"⚠️  ROI calculation failed for {address}: {e}")
                    else:
                        failed_scans += 1
                else:
                    failed_scans += 1
                    print(f"⚠️  No balance data for {address}")
                
                # Rate limiting - Etherscan allows 5 req/sec
                if i < len(addresses) - 1:
                    time.sleep(0.25)  # 4 requests per second to be safe
                    
            except Exception as e:
                failed_scans += 1
                print(f"❌ Error scanning {address}: {e}")
        
        scan_duration = time.time() - start_time
        
        return {
            'batch_name': batch_name,
            'total_addresses': len(addresses),
            'successful_scans': successful_scans,
            'failed_scans': failed_scans,
            'total_eth': total_eth,
            'scan_duration_seconds': scan_duration
        }
    
    def run_full_scan(self) -> Dict:
        """Run a full scan of all whale addresses"""
        print(f"\n🐋 Full whale scan starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        addresses = self.whale_service.whale_addresses
        total_addresses = len(addresses)
        
        print(f"📈 Scanning {total_addresses} whale addresses")
        
        # Scan all addresses
        result = self.scan_whale_batch(addresses, "Full Scan")
        
        # Update last scan time
        self.last_scan_time = datetime.now()
        
        # Print results
        print(f"\n✅ Scan completed!")
        print(f"📊 Results:")
        print(f"   • Successful scans: {result['successful_scans']}")
        print(f"   • Failed scans: {result['failed_scans']}")
        print(f"   • Total ETH tracked: {result['total_eth']:,.2f} ETH")
        print(f"   • Scan duration: {result['scan_duration_seconds']:.1f}s")
        print(f"   • Average per address: {result['scan_duration_seconds']/total_addresses:.2f}s")
        
        return result
    
    def run_background_scan(self):
        """Background thread function for periodic scanning"""
        print(f"🚀 Background whale scanner started")
        print(f"⏰ Scanning every {self.scan_interval_hours} hour(s)")
        
        while self.is_running:
            try:
                # Run scan
                self.run_full_scan()
                
                # Wait for next interval
                sleep_seconds = self.scan_interval_hours * 3600
                print(f"😴 Next scan in {self.scan_interval_hours} hour(s)")
                
                # Sleep in small intervals to allow for clean shutdown
                slept = 0
                while slept < sleep_seconds and self.is_running:
                    time.sleep(60)  # Sleep 1 minute at a time
                    slept += 60
                    
            except Exception as e:
                print(f"❌ Background scan error: {e}")
                # Sleep for 5 minutes before retry
                time.sleep(300)
    
    def start_background_scanning(self, interval_hours: int = 1):
        """Start background scanning with specified interval"""
        if self.is_running:
            print("⚠️  Background scanning already running")
            return
        
        self.scan_interval_hours = interval_hours
        self.is_running = True
        
        # Start background thread
        self.scan_thread = threading.Thread(target=self.run_background_scan, daemon=True)
        self.scan_thread.start()
        
        print(f"✅ Background whale scanning started (every {interval_hours}h)")
    
    def stop_background_scanning(self):
        """Stop background scanning"""
        if not self.is_running:
            print("ℹ️  Background scanning not running")
            return
        
        print("🛑 Stopping background whale scanner...")
        self.is_running = False
        
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5)
        
        print("✅ Background whale scanner stopped")
    
    def get_scan_status(self) -> Dict:
        """Get current scanning status"""
        return {
            'is_running': self.is_running,
            'scan_interval_hours': self.scan_interval_hours,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'total_whale_addresses': len(self.whale_service.whale_addresses),
            'thread_alive': self.scan_thread.is_alive() if self.scan_thread else False
        }

# Global instance
whale_scanner_service = WhaleScannerService() if whale_repository else None