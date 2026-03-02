from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.models import Organisation, CreditTransaction


class InsufficientCreditsError(Exception):
    def __init__(self, available: int, required: int):
        self.available = available
        self.required = required
        super().__init__(f"Insufficient credits. Required: {required}, Available: {available}")

async def deduct_credits(
    db: AsyncSession, 
    org_id: str, 
    amount: int, 
    reason: str, 
    user_id: str | None = None,
    idempotency_key: str | None = None
) -> CreditTransaction:
    """
    Checks balance, deducts atomically, and logs the transaction.
    Raises InsufficientCreditsError if balance is too low. 
    """
    if amount <= 0:
        raise ValueError("Deduction amount must be strictly positive.")

    # 1. THE LOCK: Lock the organisation row for the duration of this transaction
    org_stmt = select(Organisation).where(Organisation.id == org_id).with_for_update()
    org_result = await db.execute(org_stmt)
    org = org_result.scalar_one_or_none()
    
    if not org:
        raise ValueError("Organisation not found.")

    # 2. Calculate the current balance
    balance_stmt = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == org_id
    )
    balance_result = await db.execute(balance_stmt)
    current_balance = balance_result.scalar()

    # 3. Check if there are enough credits
    if current_balance < amount:
        raise InsufficientCreditsError(available=current_balance, required=amount)

    # 4. Insert the deduction (as a negative amount!)
    deduction = CreditTransaction(
        organisation_id=org_id,
        user_id=user_id,
        amount=-amount, # Make it negative to deduct
        reason=reason,
        idempotency_key=idempotency_key
    )
    db.add(deduction)
    
    # We flush to the database but leave the actual commit to the caller (the API route).
    # This ensures the whole process happens inside one database transaction. 
    await db.flush() 
    
    return deduction