from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app import schemas, models
from app.database import get_db

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
def send_email_draft(draft_id: int, db: Session = Depends(get_db)):
    db_draft = db.query(models.EmailDraft).options(joinedload(models.EmailDraft.task)).filter(models.EmailDraft.id == draft_id).first()
    if not db_draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    
    # Update status to Sent to simulate sending via Gmail
    db_draft.status = "Sent"
    db.commit()
    db.refresh(db_draft)
    
    # Trigger motivation notification
    notif = models.Notification(
        message=f"✉️ Negotiation Request Sent: Extension request for '{db_draft.task.title}' was sent to {db_draft.recipient}.",
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
