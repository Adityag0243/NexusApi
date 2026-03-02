from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database import get_db
from src.models.models import User, CreditTransaction
from src.dependencies import get_current_user
from src.services.credit_service import deduct_credits, InsufficientCreditsError

router = APIRouter(prefix="/api", tags=["Product API"])

# 1. Strict validation: text must be between 10 and 2000 characters
class AnalyseRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000)

@router.post("/analyse")
async def analyse_text(
    request: AnalyseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Synchronous product endpoint. Costs 25 credits."""
    required_credits = 25
    
    try:
        # 1. Deduct and commit immediately to release the DB lock!
        await deduct_credits(
            db=db, org_id=str(current_user.organisation_id),
            amount=required_credits, reason="Usage: /api/analyse",
            user_id=str(current_user.id)
        )
        await db.commit() 
    except InsufficientCreditsError as e:
        await db.rollback()
        return JSONResponse(
            status_code=402,
            content={"error": "insufficient_credits", "balance": e.available, "required": required_credits}
        )

    # 2. Dummy AI processing ( it might fail due to various reasons )
    try:
        words = request.text.split()
        word_count = len(words)
        unique_words = len(set(words))

    except Exception as e:
        # 3. IF THE AI PROCESSING FAILS, ISSUE A REFUND
        refund = CreditTransaction(
            organisation_id=current_user.organisation_id,
            user_id=current_user.id,
            amount=required_credits, # Positive amount to give it back!
            reason="Refund: /api/analyse failed" # we can even pass the reason of failure of ai processing
        )
        db.add(refund)
        await db.commit()
        
        # Tell the user what happened
        raise HTTPException(status_code=500, detail="Processing failed. Your credits have been refunded.")
        
    # 4. Success Response
    balance_stmt = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    balance_result = await db.execute(balance_stmt)
    
    return {
        "result": f"Analysis complete. Word count: {word_count}. Unique words: {unique_words}.",
        "credits_remaining": balance_result.scalar()
    }