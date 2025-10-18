# EmailSender Agent

Automatically sends emails via Gmail SMTP when JSON request files are created.

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

### JSON Request Format

```json
{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "body": "Email message content"
}
```

### Send an Email

```bash
cat > Agents/EmailSender/Requests/email.json << 'EOF'
{
  "to": "someone@example.com",
  "subject": "Hello from AI4PKM",
  "body": "This email was sent automatically!"
}
EOF
```

The agent will:
1. Detect the JSON file
2. Move to InProgress/
3. Send email via Gmail
4. Move to Completed/

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

