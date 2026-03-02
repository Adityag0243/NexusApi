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
        # 2. THIS IS WHERE WE USE YOUR SERVICE! 
        # We try to deduct 25 credits before doing any work 
        await deduct_credits(
            db=db,
            org_id=str(current_user.organisation_id),
            amount=required_credits,
            reason="Usage: /api/analyse",
            user_id=str(current_user.id)
        )
        await db.commit() # Lock in the deduction
        
    except InsufficientCreditsError as e:
        await db.rollback() # Cancel the transaction if they are broke
        # 3. Return the exact 402 error format requested by the PDF 
        return JSONResponse(
            status_code=402,
            content={
                "error": "insufficient_credits",
                "balance": e.available,
                "required": required_credits
            }
        )
        
    # 4. If we reach here, they paid! Let's do the "AI" work 
    words = request.text.split()
    word_count = len(words)
    unique_words = len(set(words))
    
    # 5. Get their new balance to show them 
    balance_stmt = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    balance_result = await db.execute(balance_stmt)
    remaining = balance_result.scalar()
    
    # Return the exact success format requested by the PDF
    return {
        "result": f"Analysis complete. Word count: {word_count}. Unique words: {unique_words}.",
        "credits_remaining": remaining
    }