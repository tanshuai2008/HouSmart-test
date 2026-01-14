
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email, EmailNotValidError
import streamlit as st

def check_email_validity(email_address):
    """
    Strictly validates an email address using email-validator.
    Returns (True, normalized_email) if valid.
    Returns (False, error_message) if invalid.
    """
    if not email_address:
        return False, "Email address is empty."
    
    try:
        # Check validity and get normalized form
        emailinfo = validate_email(email_address, check_deliverability=True) 
        normalized_email = emailinfo.normalized
        return True, normalized_email
    except EmailNotValidError as e:
        # Email is not valid, exception message is human-readable
        return False, str(e)

def send_analysis_email(to_email, subject, html_content):
    """
    Sends an email using Gmail SMTP from secrets.
    """
    # Load secrets
    smtp_user = st.secrets.get("GMAIL_USER")
    smtp_pass = st.secrets.get("GMAIL_APP_PASSWORD")
    
    if not smtp_user or not smtp_pass:
        return False, "SMTP Configuration missing (GMAIL_USER or GMAIL_APP_PASSWORD)"
    
    try:
        # Create Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email
        
        # Plain text version (optional fallback)
        text_part = MIMEText("Your HouSmart Analysis Report is attached/included as HTML.", "plain")
        
        # HTML version
        html_part = MIMEText(html_content, "html")
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send
        # Gmail SMTP: smtp.gmail.com, Port 587 (TLS) or 465 (SSL)
        # Using 587 with starttls is standard practice
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
            
        return True, "Email sent successfully."
        
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False, str(e)
