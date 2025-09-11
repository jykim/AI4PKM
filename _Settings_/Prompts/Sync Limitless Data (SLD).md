```
---
Sync missing Limitless AI lifelog data and process through PLL workflow
1. Run limitless_sync.py --sync-missing to fetch all missing data
	- Automatically detects last sync date from Ingest/Limitless/ folder
	- Syncs all missing dates from last sync to today (including today)
	- Saves data to Ingest/Limitless/{{YYYY-MM-DD}}.md for each date
	- Handles authentication and API rate limits (180 req/min)
	- Returns list of newly synced dates
2. For each newly synced date, run [[Process Life Logs (PLL)]]
	- Use "PLL for {{YYYY-MM-DD}}" for each synced date
	- Process the newly synced data from Ingest/Limitless/
	- Generate lifelog summary in AI/Lifelog/{{YYYY-MM-DD}} Lifelog.md
	- Extract meaningful moments, insights, and conversations
3. Report completion status
	- List all dates that were successfully synced and processed
	- Note any errors or missing data
	- Confirm which lifelog files were created/updated
```