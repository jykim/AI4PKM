# 최종 파일 경로: ai4pkm_cli/commands/sync_limitless_command.py

import os
import sys
import requests
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import time
import pytz
from tzlocal import get_localzone
from dotenv import load_dotenv

from ai4pkm_cli.config import Config

class SyncLimitlessCommand:
    def __init__(self, logger):
        self.logger = logger
        self.config = Config()

        load_dotenv()

        self.api_key = os.getenv("LIMITLESS_API_KEY")

        if not self.api_key:
            self.is_ready = False
            self.logger.warning("LIMITLESS_API_KEY not found in .env file. Skipping sync command.")
            return

        self.is_ready = True
        limitless_config = self.config.get('commands_config', {}).get('limitless', {})
        self.api_base_url = limitless_config.get('api_base_url', "https://api.limitless.ai/v1")
        self.output_dir = Path(limitless_config.get('output_dir', "Ingest/Limitless"))
        self.start_days_ago = limitless_config.get('start_days_ago', 7)
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_debug(self):
        """Check if logger is in debug mode."""
        return self.logger.level <= logging.DEBUG

    def run_sync(self):
        """
        Limitless 데이터 동기화를 실행하는 메인 함수.
        """
        if not hasattr(self, 'is_ready') or not self.is_ready:
            return True

        if self.is_debug:
            self.logger.debug("Starting Limitless data sync command...")
        try:
            # OS의 로컬 타임존
            local_timezone = get_localzone()
            timezone_name = str(local_timezone)
            if self.is_debug:
                self.logger.debug(f"Using local timezone: {timezone_name}")

            self.sync_missing_dates(timezone_name)

            if self.is_debug:
                self.logger.debug("Limitless data sync command finished successfully.")
            return True
        except Exception as e:
            self.logger.error(f"An error occurred during Limitless sync command: {e}")
            return False
    
    def fetch_all_lifelogs_for_day(self, date_str, timezone_str):
        all_recent_lifelogs = []
        cursor = None
        page_count = 1

        if self.is_debug:
            self.logger.debug("ℹ️  Fetching recent lifelogs...")
        while True:
            url = f"{self.api_base_url}/lifelogs"
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
                self.logger.error(f"❌ API request failed: {e}")
                if hasattr(e.response, 'text'):
                    self.logger.error(f"Response: {e.response.text}")
                return None

        if self.is_debug:
            self.logger.debug(f"✅ Retrieved {len(all_recent_lifelogs)} total recent entries. Now filtering for date {date_str}...")

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

        if self.is_debug:
            self.logger.debug(f"✅ Found {len(filtered_lifelogs)} entries matching the date {date_str}.")
        return filtered_lifelogs

    def format_lifelogs_markdown(self, lifelogs, timezone_str):
        """
        Converts lifelog data to the exact markdown format used by the Obsidian plugin.
        """
        if not lifelogs:
            return "# Limitless Data\n\nNo lifelog data available for this date.\n"
        
        local_tz = pytz.timezone(timezone_str)
        
        markdown_content = ""

        for entry in sorted(lifelogs, key=lambda x: x.get('startTime', '')):
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
        """
        Syncs data for a specific date, but only saves a file if content exists.
        """
        lifelogs = self.fetch_all_lifelogs_for_day(date_str, timezone)

        if not lifelogs:
            if self.is_debug:
                self.logger.debug(f"ℹ️ No data found for {date_str}. Skipping file creation.")
            return False

        markdown = self.format_lifelogs_markdown(lifelogs, timezone)

        if not markdown.strip():
            if self.is_debug:
                self.logger.debug(f"ℹ️ No content to save for {date_str}. Skipping file creation.")
            return False

        filepath = self.save_to_file(markdown, date_str)

        return filepath is not None

    def save_to_file(self, content, date_str):
        filepath = self.output_dir / f"{date_str}.md"
        try:
            filepath.write_text(content, encoding='utf-8')
            self.logger.info(f"📝 Saved to: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"❌ Failed to save file: {e}")
            return None
            
    def get_last_sync_date(self) -> str:
        """
        Finds the most recent date from the filenames in the output directory,
        mimicking the Obsidian plugin's behavior.
        """
        try:
            # YYYY-MM-DD.md 패턴에 맞는 파일찾기
            files = list(self.output_dir.glob("????-??-??.md"))
            if not files:
                # 파일이 하나도 없으면 7일 전부터 시작
                if self.is_debug:
                    self.logger.debug("ℹ️ No previous sync files found. Starting from 7 days ago.")
                return (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")

            # 파일 이름("YYYY-MM-DD")에서 가장 최신 날짜를 찾기
            latest_date_str = max(file.stem for file in files)
            return latest_date_str

        except Exception as e:
            self.logger.warning(f"⚠️  Error finding last sync date from files: {e}")
            return (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        
    def get_date_range(self, start_dt, end_dt):
        dates = []
        current_dt = start_dt
        while current_dt <= end_dt:
            dates.append(current_dt.strftime("%Y-%m-%d"))
            current_dt += timedelta(days=1)
        return dates

    def sync_missing_dates(self, timezone):
        """
        Syncs all days from the last synced file date up to and INCLUDING today.
        This overwrites daily notes with the latest data, just like the plugin.
        """
        last_sync_str = self.get_last_sync_date()
        last_sync_date = datetime.strptime(last_sync_str, "%Y-%m-%d").date()
        today_date = date.today()

        if self.is_debug:
            self.logger.debug(f"📅 Last sync file found: {last_sync_date.strftime('%Y-%m-%d')}")
            self.logger.debug(f"🎯 Syncing up to today: {today_date.strftime('%Y-%m-%d')}")

        if last_sync_date > today_date:
            if self.is_debug:
                self.logger.debug("✅ Last sync date is in the future. Nothing to do.")
            # 오늘 데이터는 한번 덮어써서 최신 상태를 유지합니다.
            self.sync_date(today_date.strftime("%Y-%m-%d"), timezone)
            return

        # 마지막 파일 날짜부터 오늘까지의 모든 날짜를 동기화 대상으로 설정
        dates_to_sync = self.get_date_range(last_sync_date, today_date)

        if not dates_to_sync:
            # 만약을 대비해 오늘 데이터를 한번 덮어씁니다.
            if self.is_debug:
                self.logger.debug("✅ Already up to date! Re-syncing today for good measure.")
            self.sync_date(today_date.strftime("%Y-%m-%d"), timezone)
            return

        if self.is_debug:
            self.logger.debug(f"🔄 Syncing {len(dates_to_sync)} day(s): from {dates_to_sync[0]} to {dates_to_sync[-1]}")

        for date_str in dates_to_sync:
            if self.is_debug:
                self.logger.debug(f"\n📥 Syncing {date_str}...")
            self.sync_date(date_str, timezone)

        if self.is_debug:
            self.logger.debug("\n🎉 Sync process completed.")