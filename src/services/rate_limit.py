import time
import logging
from fastapi import Request, HTTPException, Depends
import redis.asyncio as redis
from src.config import settings
from src.dependencies import get_current_user

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
logger = logging.getLogger("nexusapi")

async def check_rate_limit(request: Request, current_user = Depends(get_current_user)):
    org_id = current_user.organisation_id
    current_minute = int(time.time() / 60)
    key = f"rate_limit:{org_id}:{current_minute}"
    
    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 120)  # TTL of 2 minutes
            result = await pipe.execute()
            
        requests_this_minute = result[0]
        
        if requests_this_minute > 60:
            next_minute_start = (current_minute + 1) * 60
            retry_after = next_minute_start - int(time.time())
            
            exc = HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Maximum 60 requests per minute."
            )
            exc.headers = {"Retry-After": str(max(1, retry_after))}
            exc.error_code = "rate_limit_exceeded"
            raise exc
            
    except HTTPException:
        raise
    except Exception as e:
        # R8: Fail open requested! Allow request to proceed if Redis is unavailable.
        logger.error(f"Redis unavailable for rate limiting. Failing open: {e}")
