"""
Google OAuth2 Authentication Routes.
Handles the OAuth consent flow for Google Calendar + Gmail integration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.config import settings
from app.google_services import is_google_oauth_configured, get_oauth_flow

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/google/login")
def google_oauth_login(db: Session = Depends(get_db)):
    """
    Generates a Google OAuth2 consent URL and redirects the user.
    If credentials are not configured, returns info about standalone mode.
    """
    if not is_google_oauth_configured():
        return {
            "status": "standalone_mode",
            "message": "Google OAuth is not configured. The application runs in standalone simulation mode. "
                       "To enable real Google integration, set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
        }

    flow = get_oauth_flow()
    if not flow:
        raise HTTPException(status_code=500, detail="Failed to initialize OAuth flow")

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    # Store verifier in UserSettings
    settings_rec = db.query(models.UserSettings).first()
    if not settings_rec:
        settings_rec = models.UserSettings()
        db.add(settings_rec)
    settings_rec.google_oauth_code_verifier = flow.code_verifier
    db.commit()

    return {
        "status": "redirect",
        "authorization_url": authorization_url,
        "state": state
    }


@router.get("/google/callback")
async def google_oauth_callback(code: str = None, error: str = None, db: Session = Depends(get_db)):
    """
    Handles the OAuth2 callback from Google.
    Exchanges the authorization code for tokens and stores the refresh token.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    if not is_google_oauth_configured():
        raise HTTPException(status_code=400, detail="Google OAuth not configured")

    flow = get_oauth_flow()
    if not flow:
        raise HTTPException(status_code=500, detail="Failed to initialize OAuth flow")

    settings_rec = db.query(models.UserSettings).first()
    code_verifier = settings_rec.google_oauth_code_verifier if settings_rec else None
    if code_verifier:
        flow.code_verifier = code_verifier

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Store refresh token in UserSettings
        if not settings_rec:
            settings_rec = models.UserSettings()
            db.add(settings_rec)

        settings_rec.google_refresh_token_id = credentials.refresh_token
        settings_rec.google_account_connected = True
        db.commit()

        # Log the connection in agent activity
        from app.agents import AgentLogger
        await AgentLogger.log_activity(
            "Google OAuth",
            "Successfully connected Google Workspace account. Calendar sync and Gmail drafts are now live.",
            db
        )

        # Redirect back to the frontend instead of showing raw JSON
        frontend_url = "https://the-life-saver.vercel.app/"
        if "localhost" in settings.GOOGLE_REDIRECT_URI:
            frontend_url = "http://localhost:3000/"

        return RedirectResponse(url=frontend_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")


@router.get("/google/status")
def google_oauth_status(db: Session = Depends(get_db)):
    """Returns the current Google OAuth connection status."""
    settings_rec = db.query(models.UserSettings).first()
    
    return {
        "oauth_configured": is_google_oauth_configured(),
        "account_connected": bool(settings_rec and settings_rec.google_account_connected),
        "has_refresh_token": bool(settings_rec and settings_rec.google_refresh_token_id),
        "mode": "live" if (settings_rec and settings_rec.google_account_connected and settings_rec.google_refresh_token_id) else "simulation"
    }
