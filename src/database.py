# import os
# from dotenv import load_dotenv
# load_dotenv()

# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# # Retrieve the database URL from the environment
# DATABASE_URL = os.getenv("DATABASE_URL")
# print("\n\n\ndatabase url :: ",DATABASE_URL)
# # Create the async engine
# engine = create_async_engine(DATABASE_URL, echo=False)

# # Create a session factory
# AsyncSessionLocal = async_sessionmaker(
#     bind=engine, 
#     class_=AsyncSession, 
#     expire_on_commit=False
# )

# # This is the function the router is looking for!
# async def get_db():
#     """
#     Dependency function to yield a database session for each request.
#     It automatically closes the session when the request is done.
#     """
#     async with AsyncSessionLocal() as session:
#         yield session/

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# 1. Force Python to find the .env file exactly one folder up from 'src'
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Grab the URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")
# print("\n\n\ndatabase url :: ",DATABASE_URL)

# 3. Fail loudly if it's STILL missing
if not DATABASE_URL:
    raise ValueError(f"CRITICAL: DATABASE_URL is missing! Checked at: {env_path}")

# 4. Create the async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# 5. Create a session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db():
    """Dependency to yield a database session."""
    async with AsyncSessionLocal() as session:
        yield session