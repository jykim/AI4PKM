"""
Email Sender Agent Handler

This module is called when a .json file is created or modified in Agents/EmailSender/Requests/ folder.
Sends emails using Gmail SMTP with app password.
"""

import os
import json
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_gmail(to_email, subject, body, from_email, app_password, logger):
    """
    Send email using Gmail SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content
        from_email: Sender Gmail address
        app_password: Gmail app password
        logger: Logger instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP server
        logger.info("Connecting to Gmail SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        # Login
        logger.info("Authenticating...")
        server.login(from_email, app_password)
        
        # Send email
        logger.info("Sending email...")
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        
        # Disconnect
        server.quit()
        logger.info("✅ Email sent successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False


def process(json_content, file_path, event_type, logger, workspace_path):
    """
    Process email request from JSON content.
    
    Args:
        json_content: Parsed JSON content with email details
        file_path: Path to the JSON file (in InProgress folder)
        event_type: Type of event ('created' or 'modified')
        logger: Logger instance
        workspace_path: Path to the workspace root
    """
    logger.info(f"EmailSender: Processing {event_type} event for {os.path.basename(file_path)}")
    
    # Get Gmail credentials from environment variables
    gmail_user = os.getenv('GMAIL_USER')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    
    if not gmail_user or not gmail_app_password:
        logger.error("❌ Gmail credentials not configured!")
        logger.error("Please set environment variables:")
        logger.error("  - GMAIL_USER: Your Gmail address")
        logger.error("  - GMAIL_APP_PASSWORD: Your Gmail app password")
        logger.error("See README.md for setup instructions")
        return
    
    try:
        # Extract email details from JSON content
        to = json_content.get('to', '')
        subject = json_content.get('subject', 'No subject')
        body = json_content.get('body', '')
        
        # Validate required fields
        if not to:
            logger.error("❌ Missing 'to' field in JSON")
            return
        
        # Log email details
        logger.info("📧 Email processing:")
        logger.info(f"  - File: {os.path.basename(file_path)}")
        logger.info(f"  - Event: {event_type}")
        logger.info(f"  - From: {gmail_user}")
        logger.info(f"  - To: {to}")
        logger.info(f"  - Subject: {subject}")
        logger.info(f"  - Body preview: {body[:50]}...")
        
        # Send email
        success = send_gmail(to, subject, body, gmail_user, gmail_app_password, logger)
        
        # Log the result (file will be moved to Completed by generic handler)
        if success:
            logger.info(f"✅ Email sent successfully and will be moved to Completed folder")
        else:
            logger.warning(f"⚠️ Email sending failed but file will still be moved to Completed folder")
        
    except Exception as e:
        logger.error(f"❌ Error processing email: {e}")
        raise

