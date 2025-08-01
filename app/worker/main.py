import logging
import asyncio
import os
import sys
import signal
import time
from datetime import datetime, timedelta
import socket

from app.database.db_session import init_models
from app.worker.task_queue import get_next_task, task_completed, update_task_progress
from app.worker.worker_processors import process_task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/worker.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Worker ID
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"
logger.info(f"Worker starting with ID: {WORKER_ID}")

# Running flag
running = True

def handle_shutdown(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f"Received signal {signum}, shutting down...")
    running = False

# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

async def update_worker_heartbeat():
    """Update worker heartbeat in database"""
    try:
        from sqlalchemy import update, select
        from app.database.models import TaskWorker, WorkerStatus
        from app.database.db_session import async_session_factory
        
        async with async_session_factory() as session:
            # Check if worker exists
            query = select(TaskWorker).where(TaskWorker.worker_id == WORKER_ID)
            result = await session.execute(query)
            worker = result.scalar_one_or_none()
            
            if worker:
                # Update existing worker
                worker.last_heartbeat = datetime.utcnow()
                worker.status = WorkerStatus.IDLE
            else:
                # Create new worker
                worker = TaskWorker(
                    worker_id=WORKER_ID,
                    status=WorkerStatus.IDLE,
                    last_heartbeat=datetime.utcnow(),
                    processed_tasks=0
                )
                session.add(worker)
            
            await session.commit()
            return worker
    except Exception as e:
        logger.error(f"Error updating worker heartbeat: {e}")
        return None

async def update_worker_status(status, task_id=None):
    """Update worker status in database"""
    try:
        from sqlalchemy import update
        from app.database.models import TaskWorker
        from app.database.db_session import async_session_factory
        
        async with async_session_factory() as session:
            # Get worker
            query = update(TaskWorker).where(TaskWorker.worker_id == WORKER_ID)
            
            # Update fields
            values = {
                "status": status,
                "last_heartbeat": datetime.utcnow()
            }
            
            if task_id is not None:
                values["current_task_id"] = task_id
            
            # Execute update
            query = query.values(**values)
            await session.execute(query)
            await session.commit()
    except Exception as e:
        logger.error(f"Error updating worker status: {e}")

async def check_accounts_health():
    """Periodic check of account health"""
    try:
        from app.database.models import Account, AccountStatus
        from app.database.db_session import async_session_factory
        from sqlalchemy import select
        from app.utils.session_manager import check_account_health
        
        logger.info("Starting periodic account health check")
        
        async with async_session_factory() as session:
            # Get accounts that haven't been checked recently
            query = select(Account).where(
                Account.is_active == True,
                Account.status.in_([AccountStatus.ACTIVE, AccountStatus.LIMITED])
            )
            result = await session.execute(query)
            accounts = result.scalars().all()
            
            # Check each account
            for account in accounts:
                try:
                    logger.info(f"Checking health of account {account.id} ({account.phone})")
                    health_status = await check_account_health(account)
                    
                    # Update account status
                    account.status = health_status["status"]
                    await session.commit()
                    
                    logger.info(f"Account {account.id} health check result: {health_status['status']}")
                except Exception as e:
                    logger.error(f"Error checking account {account.id} health: {e}")
                    
                # Sleep to avoid overloading
                await asyncio.sleep(10)
    except Exception as e:
        logger.error(f"Error in account health check: {e}")

async def reset_daily_limits():
    """Reset daily usage limits at midnight"""
    try:
        from app.database.models import Account
        from app.database.db_session import async_session_factory
        from sqlalchemy import select, update
        
        logger.info("Resetting daily usage limits")
        
        async with async_session_factory() as session:
            # Reset all accounts
            query = update(Account).values(
                daily_parse_count=0,
                daily_invite_count=0,
                daily_like_count=0,
                reset_counts_at=datetime.utcnow()
            )
            await session.execute(query)
            await session.commit()
            
        logger.info("Daily limits reset complete")
    except Exception as e:
        logger.error(f"Error resetting daily limits: {e}")

async def check_cooldowns():
    """Check and expire cooldown periods"""
    try:
        from app.database.models import Account, AccountStatus
        from app.database.db_session import async_session_factory
        from sqlalchemy import select, update
        
        logger.info("Checking account cooldowns")
        
        async with async_session_factory() as session:
            # Find accounts with expired cooldown
            now = datetime.utcnow()
            query = select(Account).where(
                Account.status == AccountStatus.COOLING_DOWN,
                Account.cooldown_until <= now
            )
            result = await session.execute(query)
            accounts = result.scalars().all()
            
            # Update each account
            for account in accounts:
                account.status = AccountStatus.ACTIVE
                account.cooldown_until = None
                logger.info(f"Account {account.id} ({account.phone}) cooldown expired, now active")
            
            await session.commit()
    except Exception as e:
        logger.error(f"Error checking cooldowns: {e}")

async def run_periodic_tasks():
    """Run periodic maintenance tasks"""
    while running:
        try:
            # Update worker heartbeat
            await update_worker_heartbeat()
            
            # Get current hour
            now = datetime.utcnow()
            
            # Run tasks at appropriate times
            if now.hour == 0 and now.minute < 5:
                # Reset daily limits at midnight
                await reset_daily_limits()
            
            if now.minute < 5:
                # Check cooldowns every hour
                await check_cooldowns()
            
            if now.hour % 4 == 0 and now.minute < 10:
                # Check account health every 4 hours
                await check_accounts_health()
            
            # Sleep until next minute
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in periodic tasks: {e}")
            await asyncio.sleep(60)

async def process_tasks():
    """Main task processing loop"""
    while running:
        try:
            # Get a task from queue
            task_data = get_next_task()
            
            if not task_data:
                # No tasks, sleep and try again
                await asyncio.sleep(1)
                continue
            
            task_id = task_data["task_id"]
            logger.info(f"Processing task {task_id} of type {task_data['task_type']}")
            
            # Update worker status
            from app.database.models import WorkerStatus
            await update_worker_status(WorkerStatus.BUSY, task_id)
            
            try:
                # Process the task
                success = await process_task(task_data, 
                                            progress_callback=update_task_progress)
                
                # Mark task as completed
                task_completed(task_id, success)
                
                # Update worker status
                await update_worker_status(WorkerStatus.IDLE, None)
                
                # Update processed task count
                from app.database.models import TaskWorker
                from app.database.db_session import async_session_factory
                from sqlalchemy import select
                
                async with async_session_factory() as session:
                    query = select(TaskWorker).where(TaskWorker.worker_id == WORKER_ID)
                    result = await session.execute(query)
                    worker = result.scalar_one_or_none()
                    
                    if worker:
                        worker.processed_tasks += 1
                        await session.commit()
                
                logger.info(f"Task {task_id} completed with status: {'success' if success else 'failure'}")
            except Exception as e:
                logger.error(f"Error processing task {task_id}: {e}")
                task_completed(task_id, False, str(e))
                await update_worker_status(WorkerStatus.IDLE, None)
            
        except Exception as e:
            logger.error(f"Error in task processing loop: {e}")
            await asyncio.sleep(5)

async def main():
    """Main worker function"""
    try:
        # Initialize database models
        await init_models()
        
        # Register worker in database
        await update_worker_heartbeat()
        
        # Start periodic tasks
        periodic_task = asyncio.create_task(run_periodic_tasks())
        
        # Start processing tasks
        await process_tasks()
        
        # Cancel periodic tasks
        periodic_task.cancel()
        
    except Exception as e:
        logger.error(f"Error in worker main function: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)