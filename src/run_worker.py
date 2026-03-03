import asyncio
from arq.worker import run_worker
from src.worker import WorkerSettings

if __name__ == '__main__':
    # Manual creation of loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Starting the ARQ worker
    run_worker(WorkerSettings)