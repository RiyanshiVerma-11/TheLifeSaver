"""
Google Workspace Integration Client.
Provides real Google Calendar and Gmail API access when OAuth credentials are configured.
Falls back gracefully to simulation mode when credentials are absent.
"""

import os
import logging
import base64
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from app.config import settings

logger = logging.getLogger(__name__)

# Check if Google API client libraries are available
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import Flow
    HAS_GOOGLE_LIBS = True
except ImportError:
    HAS_GOOGLE_LIBS = False
    logger.warning("⚠️ Google API client libraries not installed. Google Workspace integration disabled.")


def is_google_oauth_configured() -> bool:
    """Returns True if Google OAuth client credentials are configured in the environment."""
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET and HAS_GOOGLE_LIBS)


def get_oauth_flow() -> Optional[Any]:
    """Creates a Google OAuth2 authorization flow for Calendar + Gmail scopes."""
    if not is_google_oauth_configured():
        return None

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    return flow


def _build_credentials(refresh_token: str) -> Optional[Any]:
    """Builds Google OAuth2 credentials from a stored refresh token."""
    if not is_google_oauth_configured() or not refresh_token:
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        creds.refresh(Request())
        return creds
    except Exception as e:
        logger.error(f"Failed to refresh Google credentials: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# GOOGLE CALENDAR CLIENT
# ──────────────────────────────────────────────────────────────

class GoogleCalendarClient:
    """Fetches real events from Google Calendar API v3."""

    def __init__(self, refresh_token: str):
        self.credentials = _build_credentials(refresh_token)

    def is_connected(self) -> bool:
        return self.credentials is not None

    def get_events(self, time_min: str, time_max: str) -> List[Dict[str, Any]]:
        """
        Fetches primary calendar events in the given time range.
        Returns a list of dicts with keys: title, start_time, end_time, source.
        """
        if not self.is_connected():
            return []

        try:
            service = build('calendar', 'v3', credentials=self.credentials, cache_discovery=False)
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=50
            ).execute()

            events = []
            for item in events_result.get('items', []):
                start = item.get('start', {})
                end = item.get('end', {})
                events.append({
                    "title": item.get('summary', 'Untitled Event'),
                    "start_time": start.get('dateTime', start.get('date', '')),
                    "end_time": end.get('dateTime', end.get('date', '')),
                    "source": "Google Calendar",
                    "is_external": True
                })
            return events
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events: {e}")
            return []


# ──────────────────────────────────────────────────────────────
# GMAIL CLIENT
# ──────────────────────────────────────────────────────────────

class GmailClient:
    """Creates real email drafts in Gmail API v1."""

    def __init__(self, refresh_token: str):
        self.credentials = _build_credentials(refresh_token)

    def is_connected(self) -> bool:
        return self.credentials is not None

    def create_draft(self, recipient: str, subject: str, body: str) -> Optional[Dict[str, Any]]:
        """
        Creates a real email draft in the user's Gmail account.
        Returns the draft metadata dict or None on failure.
        """
        if not self.is_connected():
            return None

        try:
            service = build('gmail', 'v1', credentials=self.credentials, cache_discovery=False)

            message = MIMEText(body)
            message['to'] = recipient
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            draft_body = {
                'message': {
                    'raw': raw
                }
            }

            draft = service.users().drafts().create(userId="me", body=draft_body).execute()
            logger.info(f"Gmail draft created successfully: {draft.get('id')}")
            return draft
        except Exception as e:
            logger.error(f"Error creating Gmail draft: {e}")
            return None
