#!/usr/bin/env python3
"""
Limitless AI Data Sync Script
Fetches lifelog data from Limitless AI API and saves to Ingest/Limitless/
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LIMITLESS_API_BASE = "https://api.limitless.ai/v1"
API_KEY_ENV = "LIMITLESS_API_KEY"  # Set this environment variable
OUTPUT_DIR = Path("Ingest/Limitless")

class LimitlessSync:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv(API_KEY_ENV)
        if not self.api_key:
            raise ValueError(f"API key required. Set {API_KEY_ENV} environment variable or pass api_key parameter")
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def fetch_lifelogs(self, date=None, timezone="America/Los_Angeles", limit=500):
        """
        Fetch lifelogs for a specific date
        
        Args:
            date: Date string in YYYY-MM-DD format (defaults to yesterday)
            timezone: IANA timezone string  
            limit: Maximum number of entries (max 10)
        """
        if date is None:
            # Default to yesterday
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")
        
        url = f"{LIMITLESS_API_BASE}/lifelogs"
        params = {
            "date": date,
            "timezone": timezone,
            "limit": limit
        }
        
        try:
            print(f"🔍 Fetching lifelogs for {date}...")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Retrieved {len(data.get('lifelogs', []))} lifelog entries")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return None
    
    def format_lifelog_markdown(self, data, date):
        """Convert lifelog data to markdown format"""
        if not data or 'lifelogs' not in data:
            return f"""---
date: {date}
source: Limitless AI API
tags:
  - lifelog
  - daily
---

# {date} Limitless Data

No lifelog data available for this date.
"""
        
        lifelogs = data['lifelogs']
        markdown_content = f"""---
date: {date}
source: Limitless AI API
tags:
  - lifelog
  - daily
total_entries: {len(lifelogs)}
---

# {date} Limitless Data

"""
        
        # Group by time periods
        current_hour = None
        for entry in lifelogs:
            # Extract timestamp if available
            timestamp = entry.get('timestamp', entry.get('created_at', ''))
            content = entry.get('content', entry.get('transcript', ''))
            
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour = dt.hour
                    if hour != current_hour:
                        current_hour = hour
                        time_period = self._get_time_period(hour)
                        markdown_content += f"\n## {time_period}\n\n"
                except:
                    pass
            
            # Add content
            if content:
                time_str = timestamp.split('T')[1][:5] if 'T' in timestamp else ''
                markdown_content += f"**{time_str}**: {content}\n\n"
        
        return markdown_content
    
    def _get_time_period(self, hour):
        """Convert hour to time period description"""
        if 0 <= hour < 6:
            return f"{hour:02d}:00-05:59 (새벽)"
        elif 6 <= hour < 12:
            return f"{hour:02d}:00-11:59 (오전)"
        elif 12 <= hour < 18:
            return f"{hour:02d}:00-17:59 (오후)"
        else:
            return f"{hour:02d}:00-23:59 (저녁)"
    
    def save_to_file(self, content, date):
        """Save markdown content to file"""
        filename = f"{date}.md"
        filepath = OUTPUT_DIR / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"📝 Saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to save file: {e}")
            return None
    
    def sync_date(self, date=None, timezone="America/Los_Angeles"):
        """Sync data for a specific date"""
        # Fetch data
        data = self.fetch_lifelogs(date, timezone)
        if not data:
            return False
        
        # Use the date from the API response or the requested date
        actual_date = date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Format as markdown
        markdown = self.format_lifelog_markdown(data, actual_date)
        
        # Save to file
        filepath = self.save_to_file(markdown, actual_date)
        
        return filepath is not None
    
    def get_last_sync_date(self):
        """Find the most recent date in Ingest/Limitless/ folder"""
        try:
            files = list(OUTPUT_DIR.glob("????-??-??.md"))
            if not files:
                # If no files, default to 7 days ago
                return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            # Get the most recent date from filenames
            dates = []
            for file in files:
                try:
                    date_str = file.stem  # filename without extension
                    datetime.strptime(date_str, "%Y-%m-%d")  # validate format
                    dates.append(date_str)
                except ValueError:
                    continue
            
            if dates:
                return max(dates)
            else:
                return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                
        except Exception as e:
            print(f"⚠️  Error finding last sync date: {e}")
            return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    def get_date_range(self, start_date, end_date):
        """Generate list of dates between start_date and end_date"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return dates
    
    def sync_missing_dates(self, timezone="America/Los_Angeles"):
        """Sync all missing dates since last sync"""
        last_sync = self.get_last_sync_date()
        today = datetime.now().strftime("%Y-%m-%d")
        
        print(f"📅 Last sync date: {last_sync}")
        print(f"📅 Target date: {today}")
        
        # Get next date after last sync
        last_sync_dt = datetime.strptime(last_sync, "%Y-%m-%d")
        start_date = (last_sync_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        
        if start_date > today:
            print("✅ Already up to date!")
            return []
        
        # Get all dates to sync (including today)
        dates_to_sync = self.get_date_range(start_date, today)
        synced_dates = []
        
        print(f"🔄 Need to sync {len(dates_to_sync)} dates: {dates_to_sync[0]} to {dates_to_sync[-1]}")
        
        for date in dates_to_sync:
            print(f"\n📥 Syncing {date}...")
            success = self.sync_date(date, timezone)
            if success:
                synced_dates.append(date)
                print(f"✅ Synced {date}")
            else:
                print(f"❌ Failed to sync {date}")
        
        print(f"\n🎉 Successfully synced {len(synced_dates)} out of {len(dates_to_sync)} dates")
        return synced_dates

def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync Limitless AI lifelog data")
    parser.add_argument("--date", help="Date to sync (YYYY-MM-DD), defaults to yesterday")
    parser.add_argument("--sync-missing", action="store_true", help="Sync all missing dates since last sync")
    parser.add_argument("--timezone", default="America/Los_Angeles", help="Timezone (IANA format)")
    parser.add_argument("--api-key", help="Limitless API key (or set LIMITLESS_API_KEY env var)")
    
    args = parser.parse_args()
    
    try:
        sync = LimitlessSync(api_key=args.api_key)
        
        if args.sync_missing:
            synced_dates = sync.sync_missing_dates(args.timezone)
            if synced_dates:
                print("🎉 Missing dates sync completed successfully!")
                print(f"📋 Synced dates: {', '.join(synced_dates)}")
                return 0
            else:
                print("ℹ️  No missing dates to sync")
                return 0
        else:
            success = sync.sync_date(args.date, args.timezone)
            if success:
                print("🎉 Sync completed successfully!")
                return 0
            else:
                print("❌ Sync failed")
                return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())