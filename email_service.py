"""Email service using Gmail API (OAuth2). No SMTP passwords needed."""
import os
import json
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import pytz

import config

logger = logging.getLogger("email_service")
SGT = pytz.timezone('Asia/Singapore')

GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid',
]


def _load_token() -> dict:
    """Load stored OAuth2 token from file."""
    if not os.path.exists(config.GMAIL_TOKEN_FILE):
        return {}
    with open(config.GMAIL_TOKEN_FILE, 'r') as f:
        return json.load(f)


def _save_token(data: dict):
    """Save OAuth2 token to file."""
    with open(config.GMAIL_TOKEN_FILE, 'w') as f:
        json.dump(data, f)


def get_gmail_status() -> dict:
    """Return current Gmail connection status and settings from DB."""
    token = _load_token()
    sender = token.get('sender_email', '')
    connected = bool(sender and token.get('refresh_token'))
    return {
        'connected': connected,
        'sender_email': sender,
    }


def get_gmail_credentials():
    """Get valid Google OAuth2 Credentials, refreshing token if expired.
    Returns (Credentials, error_message). error_message is None on success."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token = _load_token()
    if not token.get('refresh_token'):
        return None, "Gmail not connected. Click 'Connect Gmail' to sign in."

    creds = Credentials(
        token=token.get('token'),
        refresh_token=token.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        scopes=GMAIL_SCOPES,
    )

    # Refresh if expired
    if not creds.valid:
        try:
            creds.refresh(Request())
            token['token'] = creds.token
            _save_token(token)
        except Exception as e:
            return None, f"Token refresh failed: {e}. Please reconnect Gmail."

    return creds, None


def get_db_setting(db, key: str, default: str = '') -> str:
    from database import AppSetting
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else default


def set_db_setting(db, key: str, value: str):
    from database import AppSetting
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


def send_daily_report(db, date_str: str = None):
    """
    Generate Excel + PDF for all three tables and send via Gmail API.
    Returns (success: bool, message: str).
    """
    creds, err = get_gmail_credentials()
    if err:
        return False, err

    enabled = get_db_setting(db, 'gmail_enabled', 'false')
    if enabled != 'true':
        return False, "Daily email is disabled. Enable it in the Email settings."

    recipient = get_db_setting(db, 'gmail_recipient', '')
    if not recipient:
        return False, "No recipient email configured. Set it in the Email settings."

    token = _load_token()
    sender = token.get('sender_email', 'me')

    now_sgt = datetime.now(SGT)
    if not date_str:
        date_str = now_sgt.strftime("%Y-%m-%d")

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False, f"Invalid date: {date_str}"

    logger.info(f"[EMAIL] Generating reports for {date_str}...")

    try:
        from export_service import ExportService
        from main import _get_daily_table_for_date, _get_depreciation_data

        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        daily_data = _get_daily_table_for_date(target_date, db)
        dep_active = _get_depreciation_data("active", date_str, db)
        dep_sold = _get_depreciation_data("sold", None, db)
        cats = config.VEHICLE_CATEGORIES

        attachments = []

        for name, gen_fn, mime in [
            (f"daily_sold_{date_str}.xlsx",
             lambda: ExportService.export_daily_table_excel(daily_data),
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            (f"daily_sold_{date_str}.pdf",
             lambda: ExportService.export_daily_table_pdf(daily_data, f"SGCarMart Daily Sold - {date_str}"),
             "application/pdf"),
            (f"dep_active_{date_str}.xlsx",
             lambda d=dep_active: ExportService.export_depreciation_excel(d["data"], cats, d.get("date", date_str)),
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            (f"dep_active_{date_str}.pdf",
             lambda d=dep_active: ExportService.export_depreciation_pdf(d["data"], cats, d.get("date", date_str), "Active Listings - Depreciation / Units"),
             "application/pdf"),
            (f"dep_sold_alltime_{date_str}.xlsx",
             lambda d=dep_sold: ExportService.export_depreciation_excel(d["data"], cats, date_str),
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            (f"dep_sold_alltime_{date_str}.pdf",
             lambda d=dep_sold: ExportService.export_depreciation_pdf(d["data"], cats, date_str, "Sold Listings - Depreciation / Units (All-Time)"),
             "application/pdf"),
        ]:
            try:
                attachments.append((name, gen_fn(), mime))
            except Exception as e:
                logger.warning(f"[EMAIL] Skipped {name}: {e}")

        if not attachments:
            return False, "Failed to generate any report files."

        # Build MIME email
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"SGCarMart Daily Report - {date_str}"

        body = (
            f"<b>SGCarMart Daily Report</b><br>"
            f"Date: {date_str}<br>"
            f"Generated: {now_sgt.strftime('%Y-%m-%d %H:%M SGT')}<br><br>"
            f"<b>Attachments ({len(attachments)} files):</b><ul>"
            + "".join(f"<li>{n}</li>" for n, _, _ in attachments)
            + "</ul><small>Sent by SGCarMart Scraper</small>"
        )
        msg.attach(MIMEText(body, 'html'))

        for filename, fileobj, mimetype in attachments:
            fileobj.seek(0)
            part = MIMEBase(*mimetype.split('/'))
            part.set_payload(fileobj.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

        # Send via Gmail API
        from googleapiclient.discovery import build
        service = build('gmail', 'v1', credentials=creds)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()

        count = len(attachments)
        logger.info(f"[EMAIL] Sent to {recipient} with {count} attachments")
        return True, f"Email sent to {recipient} ({count} attachments)"

    except Exception as e:
        logger.error(f"[EMAIL] Error: {e}")
        return False, f"Failed to send email: {e}"
