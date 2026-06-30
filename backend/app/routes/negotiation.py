from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app import schemas, models
from app.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/negotiation", tags=["negotiation"])

@router.get("/drafts", response_model=List[schemas.EmailDraft])
def get_email_drafts(db: Session = Depends(get_db)):
    return db.query(models.EmailDraft).order_by(models.EmailDraft.created_at.desc()).all()

@router.put("/drafts/{draft_id}", response_model=schemas.EmailDraft)
def update_email_draft(draft_id: int, draft_update: schemas.EmailDraftBase, db: Session = Depends(get_db)):
    db_draft = db.query(models.EmailDraft).filter(models.EmailDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    
    db_draft.recipient = draft_update.recipient
    db_draft.subject = draft_update.subject
    db_draft.body = draft_update.body
    db_draft.status = draft_update.status
    db.commit()
    db.refresh(db_draft)
    return db_draft

@router.post("/send/{draft_id}", response_model=schemas.EmailDraft)
async def send_email_draft(draft_id: int, db: Session = Depends(get_db)):
    """
    Hybrid email sending:
    Mode 1 (Live): If Google OAuth is connected, creates a real Gmail draft.
    Mode 2 (Simulation): Updates status to 'Sent' locally.
    """
    db_draft = db.query(models.EmailDraft).options(joinedload(models.EmailDraft.task)).filter(models.EmailDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    
    gmail_sent = False

    # --- MODE 1: Real Gmail API ---
    settings_rec = db.query(models.UserSettings).first()
    refresh_token = settings_rec.google_refresh_token_id if settings_rec else None

    if refresh_token:
        try:
            from app.google_services import GmailClient
            client = GmailClient(refresh_token)

            if client.is_connected():
                result = client.create_draft(
                    recipient=db_draft.recipient,
                    subject=db_draft.subject,
                    body=db_draft.body
                )
                if result:
                    gmail_sent = True
                    logger.info(f"Real Gmail draft created for '{db_draft.task.title}'")

                    from app.agents import AgentLogger
                    await AgentLogger.log_activity(
                        "Gmail Integration",
                        f"Real Gmail draft created for '{db_draft.task.title}' to {db_draft.recipient}.",
                        db
                    )
        except Exception as e:
            logger.error(f"Gmail live send failed, falling back to simulation: {e}")

    # --- Update status ---
    db_draft.status = "Sent"
    db.commit()
    db.refresh(db_draft)
    
    # Trigger notification
    send_method = "via Gmail API" if gmail_sent else "simulated"
    notif = models.Notification(
        message=f"✉️ Negotiation Request Sent ({send_method}): Extension request for '{db_draft.task.title}' was sent to {db_draft.recipient}.",
        type="info",
        is_read=False
    )
    db.add(notif)
    db.commit()
    
    return db_draft

@router.delete("/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_draft(draft_id: int, db: Session = Depends(get_db)):
    db_draft = db.query(models.EmailDraft).filter(models.EmailDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    db.delete(db_draft)
    db.commit()
    return None
