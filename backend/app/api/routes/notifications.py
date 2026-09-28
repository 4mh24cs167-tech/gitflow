from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import Notification
from app.api.routes.repositories import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
async def get_notifications(current_user = Depends(get_current_user)):
    async with AsyncSessionLocal() as db:
        query = select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc())
        result = await db.execute(query)
        notifications = result.scalars().all()
        return notifications

@router.put("/{notification_id}/read")
async def mark_notification_read(notification_id: int, current_user = Depends(get_current_user)):
    async with AsyncSessionLocal() as db:
        query = select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
        result = await db.execute(query)
        notification = result.scalars().first()
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification.is_read = True
        await db.commit()
        return {"status": "success"}
