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


def process(request, logger, workspace_path):
    """
    Process email request from YAML data.
    
    Args:
        request: Parsed YAML content with email details (dict)
        logger: Logger instance
        workspace_path: Path to the workspace root
        
    Returns:
        Response dict or raises exception on error
    """
    logger.info(f"EmailSender: Processing email request")
    
    # Get Gmail credentials from environment variables
    gmail_user = os.getenv('GMAIL_USER')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    
    if not gmail_user or not gmail_app_password:
        error_msg = "Gmail credentials not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD environment variables."
        logger.error(f"❌ {error_msg}")
        logger.error("See README.md for setup instructions")
        raise ValueError(error_msg)
    
    try:
        # Extract email details from request
        to = request.get('to', '')
        subject = request.get('subject', 'No subject')
        body = request.get('body', '')
        
        # Validate required fields
        if not to:
            raise ValueError("Missing 'to' field in request")
        
        # Log email details
        logger.info("📧 Email processing:")
        logger.info(f"  - From: {gmail_user}")
        logger.info(f"  - To: {to}")
        logger.info(f"  - Subject: {subject}")
        logger.info(f"  - Body preview: {body[:50]}...")
        
        # Send email
        success = send_gmail(to, subject, body, gmail_user, gmail_app_password, logger)
        
        # Return response
        if success:
            return {
                "status": "sent",
                "to": to,
                "subject": subject,
                "message": "Email sent successfully"
            }
        else:
            raise Exception("Failed to send email")
        
    except Exception as e:
        logger.error(f"❌ Error processing email: {e}")
        raise

