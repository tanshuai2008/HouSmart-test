
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

from email.mime.image import MIMEImage

def send_analysis_email(to_email, subject, html_content, images=None):
    """
    Sends an email using Gmail SMTP from secrets.
    
    Args:
        to_email (str): Recipient email
        subject (str): Email subject
        html_content (str): HTML body
        images (dict): Optional. Dict of { 'content_id': bytes_data } to attach inline.
                       In HTML, reference as <img src="cid:content_id">
    """
    # Load secrets
    smtp_user = st.secrets.get("GMAIL_USER")
    smtp_pass = st.secrets.get("GMAIL_APP_PASSWORD")
    
    if not smtp_user or not smtp_pass:
        return False, "SMTP Configuration missing (GMAIL_USER or GMAIL_APP_PASSWORD)"
    
    try:
        # Create Message - Use 'related' for inline images
        msg = MIMEMultipart("related") 
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email
        
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        # Plain text version (optional fallback)
        text_part = MIMEText("Your HouSmart Analysis Report is attached/included as HTML.", "plain")
        msg_alternative.attach(text_part)
        
        # HTML version
        html_part = MIMEText(html_content, "html")
        msg_alternative.attach(html_part)
        
        # Attach Images
        if images:
            for cid, img_data in images.items():
                if img_data:
                    # Guess MIME type or default to png
                    img = MIMEImage(img_data)
                    # Add Content-ID header for inline referencing
                    img.add_header('Content-ID', f'<{cid}>') 
                    img.add_header('Content-Disposition', 'inline', filename=f'{cid}.png')
                    msg.attach(img)
        
        # Send
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

