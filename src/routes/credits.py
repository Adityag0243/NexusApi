from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from src.database import get_db
from src.models.models import User, CreditTransaction
from src.dependencies import get_current_user, require_role

router = APIRouter(prefix="/credits", tags=["Credits"])


# 1. Pydantic schema now expects 'reason' to match your database 
class GrantCreditsRequest(BaseModel):
    amount: int
    reason: str = "Admin manual grant" 

@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns organisation credit balance and last 10 transactions."""
    
    # 1. Calculate the total balance
    balance_stmt = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    balance_result = await db.execute(balance_stmt)
    balance = balance_result.scalar()
    
    # 2. Fetch the last 10 transactions 
    tx_stmt = select(CreditTransaction).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    ).order_by(CreditTransaction.created_at.desc()).limit(10)
    
    tx_result = await db.execute(tx_stmt)
    transactions = tx_result.scalars().all()
    
    # 3. Format and return the response
    return {
        "organisation_id": str(current_user.organisation_id), 
        "balance": balance,
        "transactions": [
            {
                "id": str(tx.id),
                "amount": tx.amount,
                "reason": tx.reason,
                "created_at": tx.created_at
            }
            for tx in transactions
        ]
    }


@router.post("/grant", dependencies=[Depends(require_role("admin"))])
async def grant_credits(
    request: GrantCreditsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Grants credits to the user's organisation (Admin only)."""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive.")
        
    # 2. We now pass user_id and reason exactly as your model expects them!
    new_transaction = CreditTransaction(
        organisation_id=current_user.organisation_id,
        user_id=current_user.id,
        amount=request.amount,
        reason=request.reason
    )
    
    db.add(new_transaction)
    await db.commit()
    
    return {
        "message": f"Successfully granted {request.amount} credits.", 
        "reason": request.reason
    }