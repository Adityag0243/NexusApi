from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job
from arq.constants import job_key_prefix

from src.database import get_db
from src.config import settings
from src.models.models import User, CreditTransaction
from src.dependencies import get_current_user, cookie_sec
from src.services.credit_service import deduct_credits, InsufficientCreditsError
from src.services.rate_limit import check_rate_limit


router = APIRouter(
    prefix="/api", 
    tags=["Product API"],
    dependencies=[Depends(check_rate_limit)]
)

# 1. Strict validation: text must be between 10 and 2000 characters
class AnalyseRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000)

@router.post("/analyse")
async def analyse_text(
    request: AnalyseRequest,
    req: Request,
    auth_cookie: str = Depends(cookie_sec),
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
            content={
                "error": "insufficient_credits", 
                "message": f"Insufficient credits. Balance: {e.available}, Required: {required_credits}",
                "request_id": getattr(req.state, "request_id", "unknown")
            }
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



class SummariseRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000)

@router.post("/summarise")
async def summarise_text(
    request: SummariseRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Async product endpoint. Costs 10 credits. Returns a job_id."""
    required_credits = 10
    
    # 1. Deduct credits immediately ( lock and commit )
    try:
        await deduct_credits(
            db=db, org_id=str(current_user.organisation_id),
            amount=required_credits, reason="Usage: /api/summarise",
            user_id=str(current_user.id)
        )
        await db.commit()
    except InsufficientCreditsError as e:
        await db.rollback()
        return JSONResponse(
            status_code=402,
            content={
                "error": "insufficient_credits", 
                "message": f"Insufficient credits. Balance: {e.available}, Required: {required_credits}",
                "request_id": getattr(req.state, "request_id", "unknown")
            }
        )

    # 2. Connect to the Redis
    redis_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    
    # 3. Pin the job to the rail! 
    job = await redis_pool.enqueue_job(
        'summarise_task', # This is the name of the Chef's recipe
        request.text, 
        org_id=str(current_user.organisation_id),
        user_id=str(current_user.id)
    )
    
    # 4. Hand the user their Pager immediately (under 200ms!)
    return {"job_id": job.job_id}


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Polls job status. Returns result when completed."""
    redis_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    job = Job(job_id, redis_pool)
    
    # 1. Check if the job actually exists
    try:
        status = await job.status()
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if status.value == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    # 2. SECURITY CHECK: Only the organisation that created it can view it! 
    info = await job.info()
    if info and info.kwargs.get('org_id') != str(current_user.organisation_id):
        raise HTTPException(status_code=403, detail="You do not have permission to view this job.")

    # 3. Read the pager status
    response = {"job_id": job_id, "status": status.value}
    
    # If the Chef is done, get the result or the error
    if status.value == "complete":
        result = await job.result_info()
        if result.success:
            response["result"] = result.result
        else:
            response["status"] = "failed"
            response["error"] = "Background processing failed."
            
    return response