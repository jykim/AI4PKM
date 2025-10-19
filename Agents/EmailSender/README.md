# EmailSender Agent

Automatically sends emails via Gmail SMTP when YAML request files are created.

## Setup

### 1. Create Gmail App Password

1. Go to https://myaccount.google.com/
2. **Security** → **2-Step Verification** (enable first)
3. Scroll to **App passwords**
4. Generate app password for "Mail"
5. Copy 16-character password

### 2. Set Environment Variables

Add to `~/.zshrc` or `~/.bash_profile`:

```bash
export GMAIL_USER="your-email@gmail.com"
export GMAIL_APP_PASSWORD="your-16-char-password"
```

Reload shell:
```bash
source ~/.zshrc
```

## Usage

### YAML Request Format

```yaml
to: recipient@example.com
subject: Email Subject
body: |
  Email message content
  Can be multiple lines
```

### Send an Email

```bash
cat > Agents/EmailSender/Requests/email.yaml << 'EOF'
to: someone@example.com
subject: Hello from AI4PKM
body: |
  This email was sent automatically!
  
  The agent processed the YAML request and sent this email via Gmail.
EOF
```

The agent will:
1. Detect the YAML file
2. Send email via Gmail
3. Save result to Completed/ with request/response
4. Remove original file from Requests/

### Example Result

After processing, check `Completed/` folder:

**Success:**
```yaml
request:
  to: someone@example.com
  subject: Hello from AI4PKM
  body: |
    This email was sent automatically!
response:
  status: sent
  to: someone@example.com
  subject: Hello from AI4PKM
  message: Email sent successfully
timestamp: '2025-10-18T00:20:15.123456'
```

**Error:**
```yaml
request:
  to: someone@example.com
  subject: Test
error: "Gmail credentials not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD environment variables."
timestamp: '2025-10-18T00:20:15.123456'
```

## Troubleshooting

**"Gmail credentials not configured"**
- Check environment variables: `echo $GMAIL_USER`
- Restart terminal after setting

**"Authentication failed"**
- Use app password, not regular password
- Enable 2-Step Verification first
- Regenerate app password if needed

**"SMTP connection error"**
- Check internet connection
- Verify Gmail SMTP not blocked by firewall
