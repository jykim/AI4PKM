#!/usr/bin/env python3
"""
Limitless AI Data Sync Script (Final, Final Corrected Version)
Mimics the successful curl command exactly.
"""

import os
import sys
import requests
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv
import time
import pytz

# Configuration
load_dotenv()
LIMITLESS_API_BASE = "https://api.limitless.ai/v1"
API_KEY_ENV = "LIMITLESS_API_KEY"
OUTPUT_DIR = Path("Ingest/Limitless")
STATE_FILE = Path("_Settings/limitless_last_sync.txt")

class LimitlessSync:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv(API_KEY_ENV)
        if not self.api_key:
            raise ValueError(f"API key required. Set {API_KEY_ENV} environment variable.")
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_all_lifelogs_for_day(self, date_str, timezone_str):
        all_recent_lifelogs = []
        cursor = None
        page_count = 1
        
        print("ℹ️  Fetching recent lifelogs...")
        while True:
            url = f"{LIMITLESS_API_BASE}/lifelogs"
            params = { "limit": 10 }
            if cursor:
                params['cursor'] = cursor

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                lifelogs_page = data.get('data', {}).get('lifelogs', [])
                if not lifelogs_page:
                    break
                
                all_recent_lifelogs.extend(lifelogs_page)

                cursor = data.get('meta', {}).get('lifelogs', {}).get('nextCursor')
                if not cursor or page_count > 10:
                    break
                
                page_count += 1
                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                print(f"❌ API request failed: {e}")
                if hasattr(e.response, 'text'): print(f"Response: {e.response.text}")
                return None
        
        print(f"✅ Retrieved {len(all_recent_lifelogs)} total recent entries. Now filtering for date {date_str}...")

        target_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        local_tz = pytz.timezone(timezone_str)
        
        filtered_lifelogs = []
        for log in all_recent_lifelogs:
            start_time_utc_str = log.get('startTime')
            if not start_time_utc_str:
                continue
            
            utc_dt = datetime.fromisoformat(start_time_utc_str.replace('Z', '+00:00'))
            local_dt = utc_dt.astimezone(local_tz)
            
            if local_dt.date() == target_date_obj:
                filtered_lifelogs.append(log)
        
        print(f"✅ Found {len(filtered_lifelogs)} entries matching the date {date_str}.")
        return filtered_lifelogs

    def format_lifelogs_markdown(self, lifelogs, timezone_str):
        """
        Converts lifelog data to the exact markdown format used by the Obsidian plugin.
        """
        if not lifelogs:
            return "# Limitless Data\n\nNo lifelog data available for this date.\n"
        
        # 타임존 객체를 미리 만들어 둡니다.
        local_tz = pytz.timezone(timezone_str)
        
        # 최종 Markdown 내용을 담을 변수
        markdown_content = ""

        # lifelog를 시간 순서대로 정렬
        for entry in sorted(lifelogs, key=lambda x: x.get('startTime', '')):
            # 상세 contents가 있는 경우에만 처리
            contents = entry.get('contents', [])
            if not contents:
                continue

            for item in contents:
                item_type = item.get('type')
                content = item.get('content', '').strip()
                speaker = item.get('speakerName', 'Unknown')
                timestamp_utc_str = item.get('startTime')

                if not content:
                    continue

                # 타입에 따라 다른 Markdown 형식 적용
                if item_type == 'heading1':
                    markdown_content += f"# {content}\n"
                elif item_type == 'heading2':
                    markdown_content += f"## {content}\n"
                elif item_type == 'blockquote':
                    time_display = ""
                    if timestamp_utc_str:
                        try:
                            utc_dt = datetime.fromisoformat(timestamp_utc_str.replace('Z', '+00:00'))
                            local_dt = utc_dt.astimezone(local_tz)
                            # 플러그인 형식: "9/10/25 7:40 PM"
                            time_display = local_dt.strftime("%-m/%-d/%y %-I:%M %p")
                        except (ValueError, TypeError):
                            pass
                    
                    # 최종 출력 형식: "- Unknown (9/10/25 7:40 PM): 내용"
                    markdown_content += f"- {speaker} ({time_display}): {content}\n"
        
        return markdown_content.strip()

    def sync_date(self, date_str, timezone):
        lifelogs = self.fetch_all_lifelogs_for_day(date_str, timezone)
        if lifelogs is None:
            return False
        
        markdown = self.format_lifelogs_markdown(lifelogs, timezone)
        filepath = self.save_to_file(markdown, date_str)
        return filepath is not None

    def save_to_file(self, content, date_str):
        filepath = OUTPUT_DIR / f"{date_str}.md"
        try:
            filepath.write_text(content, encoding='utf-8')
            print(f"📝 Saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to save file: {e}")
            return None
            
    def get_last_sync_date(self) -> date:
        try:
            return datetime.strptime(STATE_FILE.read_text().strip(), "%Y-%m-%d").date()
        except (FileNotFoundError, ValueError):
            return date.today() - timedelta(days=7)

    def _set_last_sync_date(self, new_date: date):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(new_date.strftime("%Y-%m-%d"))
        
    def get_date_range(self, start_dt, end_dt):
        dates = []
        current_dt = start_dt
        while current_dt <= end_dt:
            dates.append(current_dt.strftime("%Y-%m-%d"))
            current_dt += timedelta(days=1)
        return dates

    def sync_missing_dates(self, timezone):
        last_sync_date = self.get_last_sync_date()
        yesterday_date = date.today() - timedelta(days=1)
        
        if last_sync_date >= yesterday_date:
            print("✅ Already up to date!")
            return []
        
        start_date = last_sync_date + timedelta(days=1)
        dates_to_sync = self.get_date_range(start_date, yesterday_date)
        
        for date_str in dates_to_sync:
            print(f"\n📥 Syncing {date_str}...")
            success = self.sync_date(date_str, timezone)
            if success:
                self._set_last_sync_date(datetime.strptime(date_str, "%Y-%m-%d").date())
            else:
                print(f"❌ Failed to sync {date_str}. Stopping.")
                break

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync Limitless AI lifelog data")
    parser.add_argument("--date", help="Date to sync (YYYY-MM-DD)")
    parser.add_argument("--sync-missing", action="store_true", help="Sync all missing dates since last sync")
    parser.add_argument("--timezone", default="America/Los_Angeles", help="Your local IANA timezone")
    
    args = parser.parse_args()
    
    sync = LimitlessSync()
    if args.sync_missing:
        sync.sync_missing_dates(args.timezone)
    else:
        target_date = args.date or (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        sync.sync_date(target_date, args.timezone)

if __name__ == "__main__":
    sys.exit(main())