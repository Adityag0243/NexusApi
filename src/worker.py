import asyncio
from arq.connections import RedisSettings
from src.database import AsyncSessionLocal
from src.models.models import CreditTransaction
from src.config import settings

async def summarise_task(ctx, text: str, org_id: str, user_id: str):
    """The actual background job executed by the ARQ worker."""
    
    try:
        # 1. Simulating heavy AI processing
        await asyncio.sleep(2) 
        
        # Can Simulate a random failure for testing purposes
        # raise ValueError("AI Model Timeout")
        
        summary = f"Summary of {len(text.split())} words."
        return summary

    except Exception as e:
        # 2. EXPLICIT FAILURE HANDLING: Issue a refund!
        async with AsyncSessionLocal() as db:
            refund = CreditTransaction(
                organisation_id=org_id,
                user_id=user_id,
                amount=10,  # Refund the 10 credits deducted in api.py
                reason=f"Refund: Background job failed. Error: {str(e)}"
            )
            db.add(refund)
            await db.commit()
            
        # Re-raise the exception so ARQ marks the job status as 'failed'
        raise e

# ARQ Worker Configuration
class WorkerSettings:
    functions = [summarise_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)