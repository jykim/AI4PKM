# Scheduler Agent

Schedules one-time request file creation for other agents at specified times.

## Use Case

Need to send an email at a specific time? Or trigger any agent in the future? Use the Scheduler!

## YAML Request Format

```yaml
target_agent: EmailSender           # Which agent to send request to
scheduled_time: "2025-10-18 20:00:00"  # When to create the request (YYYY-MM-DD HH:MM:SS)
request_data:                        # The actual request for the target agent
  to: gpminsuk@gmail.com
  subject: Scheduled Email
  body: |
    This email was scheduled to be sent at a specific time!
```

## Usage Examples

### Schedule an Email

```bash
cat > Agents/Scheduler/Requests/schedule-email.yaml << 'EOF'
target_agent: EmailSender
scheduled_time: "2025-10-18 20:00:00"
request_data:
  to: gpminsuk@gmail.com
  subject: Scheduled Email
  body: |
    This email was scheduled in advance!
    
    It was automatically sent at the scheduled time.
EOF
```

### Schedule for Another Agent

```yaml
target_agent: HelloWorld
scheduled_time: "2025-10-19 09:00:00"
request_data:
  message: Good morning!
  task: daily_greeting
```

## How It Works

1. Drop YAML file in `Requests/`
2. Scheduler validates:
   - Target agent exists
   - Time is in the future
   - Not scheduling to itself (prevents infinite loop)
3. Sets up one-time timer
4. At scheduled time, creates request file in target agent's `Requests/` folder
5. Target agent processes automatically

## Example Result in Completed/

```yaml
request:
  target_agent: EmailSender
  scheduled_time: '2025-10-18 20:00:00'
  request_data:
    to: gpminsuk@gmail.com
    subject: Scheduled Email
    body: |
      This email was scheduled in advance!
response:
  status: scheduled
  target_agent: EmailSender
  scheduled_time: '2025-10-18T20:00:00'
  delay_seconds: 3542.5
  message: Request will be sent to EmailSender at 2025-10-18 20:00:00
timestamp: '2025-10-18T19:01:17.123456'
```

## Time Formats Supported

- **Standard**: `"2025-10-18 20:00:00"`
- **ISO format**: `"2025-10-18T20:00:00"`

## Important Notes

- ⚠️ **One-time only** - Not a recurring schedule (use cron for that)
- ⚠️ **Requires running process** - The `ai4pkm -c` must keep running until scheduled time
- ⚠️ **Cannot schedule to Scheduler** - Prevents infinite loops
- ✅ **Validates target agent** - Checks agent folder exists
- ✅ **Validates time** - Must be in the future

## Limitations

- If `ai4pkm -c` is stopped before the scheduled time, the schedule is lost
- For persistent schedules across restarts, use the main cron system instead
- This is best for short-term, one-time scheduling needs

## Error Handling

**Invalid target agent:**
```yaml
error: |
  Target agent 'NonExistent' does not exist at Agents/NonExistent
```

**Time in the past:**
```yaml
error: |
  Scheduled time must be in the future. Given: 2025-10-18 10:00:00, Now: 2025-10-18 19:00:00
```

**Missing fields:**
```yaml
error: |
  Missing 'scheduled_time' field
```

