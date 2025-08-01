import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Callable, Dict, Any

from app.database.db_session import async_session_factory
from app.database.models import Task, TaskStatus, Account, AccountStatus, ParsedData, TaskResult
from app.utils.session_manager import get_client_session, close_client_session

# Configure logging
logger = logging.getLogger(__name__)

async def process_task(task_data: Dict[str, Any], progress_callback: Callable = None) -> bool:
    """
    Process a task based on its type
    
    Args:
        task_data: Task data from queue
        progress_callback: Callback function to update progress
        
    Returns:
        bool: True if successful, False otherwise
    """
    task_id = task_data["task_id"]
    task_type = task_data["task_type"]
    
    # Update task status to running
    async with async_session_factory() as session:
        task = await session.get(Task, task_id)
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return False
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        await session.commit()
    
    # Call appropriate processor based on task type
    try:
        if task_type == "parse_members":
            return await process_parse_members(task_data, progress_callback)
        elif task_type == "parse_writers":
            return await process_parse_writers(task_data, progress_callback)
        elif task_type == "parse_commenters":
            return await process_parse_commenters(task_data, progress_callback)
        elif task_type == "invite_users":
            return await process_invite_users(task_data, progress_callback)
        elif task_type == "like_comments":
            return await process_like_comments(task_data, progress_callback)
        else:
            logger.error(f"Unknown task type: {task_type}")
            return False
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}")
        return False

async def get_account_for_task(task_data: Dict[str, Any], increment_field: str) -> Account:
    """
    Get an available account for task
    
    Args:
        task_data: Task data from queue
        increment_field: Field to increment (daily_parse_count, daily_invite_count, etc)
        
    Returns:
        Account: Available account or None
    """
    account_ids = task_data["params"].get("account_ids", [])
    
    if not account_ids:
        logger.error("No account IDs provided for task")
        return None
    
    async with async_session_factory() as session:
        # Try each account in order
        for account_id in account_ids:
            account = await session.get(Account, account_id)
            
            if not account:
                logger.warning(f"Account {account_id} not found")
                continue
            
            # Check if account is active and not in cooldown
            if account.status != AccountStatus.ACTIVE:
                logger.info(f"Account {account_id} is not active (status: {account.status})")
                continue
            
            if account.cooldown_until and account.cooldown_until > datetime.utcnow():
                logger.info(f"Account {account_id} is in cooldown until {account.cooldown_until}")
                continue
            
            # Account is available, increment usage counter
            setattr(account, increment_field, getattr(account, increment_field) + 1)
            account.last_used = datetime.utcnow()
            
            # Check if account should go into cooldown
            from app.api.routes.settings import get_user_settings
            user_id = task_data["user_id"]
            settings = await get_user_settings(user_id, session)
            
            if increment_field == "daily_parse_count" and account.daily_parse_count >= settings.max_parse_per_account:
                account.status = AccountStatus.COOLING_DOWN
                account.cooldown_until = datetime.utcnow() + timedelta(hours=settings.cooldown_hours)
                logger.info(f"Account {account_id} reached parsing limit, set to cooldown for {settings.cooldown_hours} hours")
            
            elif increment_field == "daily_invite_count" and account.daily_invite_count >= settings.max_invite_per_account:
                account.status = AccountStatus.COOLING_DOWN
                account.cooldown_until = datetime.utcnow() + timedelta(hours=settings.cooldown_hours)
                logger.info(f"Account {account_id} reached invite limit, set to cooldown for {settings.cooldown_hours} hours")
            
            elif increment_field == "daily_like_count" and account.daily_like_count >= 200:  # Hardcoded limit for likes
                account.status = AccountStatus.COOLING_DOWN
                account.cooldown_until = datetime.utcnow() + timedelta(hours=settings.cooldown_hours)
                logger.info(f"Account {account_id} reached like limit, set to cooldown for {settings.cooldown_hours} hours")
            
            await session.commit()
            return account
    
    # No available accounts
    logger.error("No available accounts found for task")
    return None

async def process_parse_members(task_data: Dict[str, Any], progress_callback: Callable) -> bool:
    """
    Process parse members task
    
    Args:
        task_data: Task data from queue
        progress_callback: Callback function to update progress
        
    Returns:
        bool: True if successful, False otherwise
    """
    task_id = task_data["task_id"]
    params = task_data["params"]
    target = params.get("target", "")
    limit = params.get("limit", 0)
    
    if not target:
        logger.error(f"No target specified for parse members task {task_id}")
        return False
    
    # Get an account for parsing
    account = await get_account_for_task(task_data, "daily_parse_count")
    if not account:
        logger.error(f"No available account for parse members task {task_id}")
        return False
    
    try:
        # Get Telegram client session
        client = await get_client_session(account)
        if not client:
            logger.error(f"Failed to create client session for account {account.id}")
            return False
        
        # Clean up target
        if target.startswith("@"):
            target = target[1:]
        elif "t.me/" in target:
            target = target.split("t.me/")[1].split("/")[0]
        
        # Get entity
        entity = await client.get_entity(target)
        
        # Get participants
        members = []
        total_retrieved = 0
        batch_size = 200  # Telegram's limitation per request
        
        # Initialize progress
        if progress_callback:
            progress_callback(task_id, 0, limit if limit > 0 else None, f"Starting to parse members from {target}")
        
        # Parse members in batches
        offset = 0
        participant_count = 0
        
        while True:
            try:
                batch = await client(GetParticipantsRequest(
                    entity, ChannelParticipantsSearch(''), offset, batch_size, hash=0
                ))
                
                if not batch.users:
                    break
                
                members.extend(batch.users)
                offset += len(batch.users)
                total_retrieved += len(batch.users)
                participant_count = batch.count
                
                # Update progress
                if progress_callback:
                    progress = int(total_retrieved / (limit or participant_count) * 100)
                    progress_callback(
                        task_id, 
                        min(progress, 100),  # Ensure progress doesn't exceed 100
                        participant_count,
                        f"Retrieved {total_retrieved} members from {target}"
                    )
                
                # Check if we've reached the limit or all participants
                if limit > 0 and total_retrieved >= limit:
                    break
                
                if total_retrieved >= participant_count:
                    break
                
                # Sleep to avoid hitting rate limits
                await asyncio.sleep(2)
                
            except FloodWaitError as e:
                # Handle rate limiting
                logger.warning(f"FloodWaitError in parse_members: {e}")
                
                if progress_callback:
                    progress_callback(
                        task_id,
                        None,
                        None,
                        f"Rate limited, waiting for {e.seconds} seconds"
                    )
                
                await asyncio.sleep(e.seconds)
                
            except Exception as e:
                logger.error(f"Error parsing members batch: {e}")
                
                # Continue with next batch
                if total_retrieved > 0:
                    continue
                else:
                    return False
        
        # Save results to database
        async with async_session_factory() as session:
            # Save each member
            for member in members:
                parsed_data = ParsedData(
                    task_id=task_id,
                    data_type="member",
                    username=member.username,
                    user_id=str(member.id),
                    first_name=member.first_name,
                    last_name=member.last_name,
                    parsed_at=datetime.utcnow(),
                    source=target
                )
                session.add(parsed_data)
            
            # Create result file
            import os
            import csv
            from app.worker.export import export_to_csv
            
            # Ensure results directory exists
            results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
            os.makedirs(results_dir, exist_ok=True)
            
            # Create CSV file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"members_{target}_{timestamp}.csv"
            filepath = os.path.join(results_dir, filename)
            
            # Export data to CSV
            export_to_csv(members, filepath)
            
            # Create task result
            task_result = TaskResult(
                task_id=task_id,
                result_type="csv",
                file_path=filepath,
                items_count=len(members),
                created_at=datetime.utcnow()
            )
            session.add(task_result)
            
            # Update task
            task = await session.get(Task, task_id)
            if task:
                task.total_items = len(members)
                task.result_file = filepath
            
            await session.commit()
        
        # Update progress to complete
        if progress_callback:
            progress_callback(
                task_id, 
                100, 
                len(members),
                f"Completed parsing {len(members)} members from {target}"
            )
        
        # Close client session
        await close_client_session(account)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing parse members task {task_id}: {e}")
        
        # Close client session if exists
        if account:
            await close_client_session(account)
            
        return False

async def process_parse_writers(task_data: Dict[str, Any], progress_callback: Callable) -> bool:
    """
    Process parse writers task (channel post authors)
    
    Args:
        task_data: Task data from queue
        progress_callback: Callback function to update progress
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Similar implementation to process_parse_members
    # but focused on getting authors from channel posts
    
    task_id = task_data["task_id"]
    params = task_data["params"]
    target = params.get("target", "")
    limit = params.get("limit", 0)
    
    if not target:
        logger.error(f"No target specified for parse writers task {task_id}")
        return False
    
    # Implementation would follow similar pattern to parse_members
    # with adaptations for extracting post authors
    
    # Placeholder for the actual implementation
    if progress_callback:
        progress_callback(task_id, 100, 0, "Writers parsing not yet implemented")
    
    return True

async def process_parse_commenters(task_data: Dict[str, Any], progress_callback: Callable) -> bool:
    """
    Process parse commenters task
    
    Args:
        task_data: Task data from queue
        progress_callback: Callback function to update progress
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Similar implementation to process_parse_members
    # but focused on getting users who commented on posts
    
    task_id = task_data["task_id"]
    params = task_data["params"]
    target = params.get("target", "")
    limit = params.get("limit", 0)
    
    if not target:
        logger.error(f"No target specified for parse commenters task {task_id}")
        return False
    
    # Implementation would follow similar pattern to parse_members
    # with adaptations for extracting commenters
    
    # Placeholder for the actual implementation
    if progress_callback:
        progress_callback(task_id, 100, 0, "Commenters parsing not yet implemented")
    
    return True

async def process_invite_users(task_data: Dict[str, Any], progress_callback: Callable) -> bool:
    """
    Process invite users task
    
    Args:
        task_data: Task data from queue
        progress_callback: Callback function to update progress
        
    Returns:
        bool: True if successful, False otherwise
    """
    task_id = task_data["task_id"]
    params = task_data["params"]
    target = params.get("target", "")
    delay_min = params.get("delay_min", 30)
    delay_max = params.get("delay_max", 60)
    
    # Get users to invite
    usernames = []
    
    # Source can be either a database or external list
    if "source_db_id" in params:
        # Get users from database
        source_db_id = params["source_db_id"]
        
        async with async_session_factory() as session:
            # Get parsed data from source task
            from sqlalchemy import select
            from app.database.models import ParsedData
            
            query = select(ParsedData).where(ParsedData.task_id == source_db_id)
            result = await session.execute(query)
            parsed_data = result.scalars().all()
            
            # Extract usernames
            for data in parsed_data:
                if data.username:
                    usernames.append(data.username)
    
    elif "usernames" in params:
        # Use provided usernames
        usernames = params["usernames"]
    
    if not usernames:
        logger.error(f"No users to invite for task {task_id}")
        return False
    
    # Get target group/channel
    if not target:
        logger.error(f"No target specified for invite task {task_id}")
        return False
    
    # Clean up target
    if target.startswith("@"):
        target = target[1:]
    elif "t.me/" in target:
        target = target.split("t.me/")[1].split("/")[0]
    
    # Get an account for inviting
    account = await get_account_for_task(task_data, "daily_invite_count")
    if not account:
        logger.error(f"No available account for invite task {task_id}")
        return False
    
    try:
        # Get Telegram client session
        client = await get_client_session(account)
        if not client:
            logger.error(f"Failed to create client session for account {account.id}")
            return False
        
        # Get target entity
        entity = await client.get_entity(target)
        
        # Initialize counters
        total = len(usernames)
        invited = 0
        failed = 0
        
        # Initialize progress
        if progress_callback:
            progress_callback(task_id, 0, total, f"Starting to invite users to {target}")
        
        # Invite users one by one
        for username in usernames:
            try:
                # Get user entity
                user = await client.get_entity(username)
                
                # Invite user
                await client(InviteToChannelRequest(entity, [user]))
                
                # Update counters
                invited += 1
                
                # Update progress
                if progress_callback:
                    progress = int(invited / total * 100)
                    progress_callback(
                        task_id, 
                        progress,
                        total,
                        f"Invited {invited}/{total} users to {target}"
                    )
                
                # Random delay between invites
                delay = random.randint(delay_min, delay_max)
                await asyncio.sleep(delay)
                
            except UserAlreadyParticipantError:
                # User already in the group
                invited += 1
                
                if progress_callback:
                    progress = int(invited / total * 100)
                    progress_callback(
                        task_id, 
                        progress,
                        total,
                        f"User {username} already in {target}, skipping... ({invited}/{total})"
                    )
                
            except FloodWaitError as e:
                # Handle rate limiting
                logger.warning(f"FloodWaitError in invite_users: {e}")
                
                if progress_callback:
                    progress_callback(
                        task_id,
                        None,
                        None,
                        f"Rate limited, waiting for {e.seconds} seconds"
                    )
                
                await asyncio.sleep(e.seconds)
                
                # Try again with this user
                continue
                
            except Exception as e:
                # Failed to invite user
                logger.error(f"Error inviting user {username}: {e}")
                failed += 1
                
                if progress_callback:
                    progress = int(invited / total * 100)
                    progress_callback(
                        task_id, 
                        progress,
                        total,
                        f"Failed to invite {username}: {str(e)[:50]}... ({invited}/{total})"
                    )
                
                # Continue with next user
                continue
        
        # Update task results
        async with async_session_factory() as session:
            task = await session.get(Task, task_id)
            if task:
                task.total_items = total
                task.logs = f"Invited: {invited}, Failed: {failed}"
                await session.commit()
        
        # Update progress to complete
        if progress_callback:
            progress_callback(
                task_id, 
                100, 
                total,
                f"Completed inviting users to {target}. Successful: {invited}, Failed: {failed}"
            )
        
        # Close client session
        await close_client_session(account)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing invite users task {task_id}: {e}")
        
        # Close client session if exists
        if account:
            await close_client_session(account)
            
        return False

async def process_like_comments(task_data: Dict[str, Any], progress_callback: Callable) -> bool:
    """
    Process like comments task
    
    Args:
        task_data: Task data from queue
        progress_callback: Callback function to update progress
        
    Returns:
        bool: True if successful, False otherwise
    """
    task_id = task_data["task_id"]
    params = task_data["params"]
    target = params.get("target", "")
    delay_min = params.get("delay_min", 5)
    delay_max = params.get("delay_max", 15)
    limit_per_account = params.get("limit_per_account", 100)
    
    if not target:
        logger.error(f"No target specified for like comments task {task_id}")
        return False
    
    # Get an account for liking
    account = await get_account_for_task(task_data, "daily_like_count")
    if not account:
        logger.error(f"No available account for like comments task {task_id}")
        return False
    
    try:
        # Get Telegram client session
        client = await get_client_session(account)
        if not client:
            logger.error(f"Failed to create client session for account {account.id}")
            return False
        
        # Clean up target
        if target.startswith("@"):
            channel_name = target[1:]
            # Get recent posts from channel
            posts = await client(GetHistoryRequest(
                peer=channel_name,
                offset_id=0,
                offset_date=None,
                add_offset=0,
                limit=10,  # Get 10 recent posts
                max_id=0,
                min_id=0,
                hash=0
            ))
            
            # For each post, get and like comments
            total_comments = 0
            liked_comments = 0
            
            # Update progress
            if progress_callback:
                progress_callback(task_id, 0, None, f"Starting to like comments in {target}")
            
            # Process each post
            for i, post in enumerate(posts.messages):
                if progress_callback:
                    progress_callback(
                        task_id, 
                        int((i / len(posts.messages)) * 50),  # First half of progress for fetching
                        None,
                        f"Processing post {i+1}/{len(posts.messages)} in {target}"
                    )
                
                # Get comments for this post
                try:
                    comments = await client(GetRepliesRequest(
                        peer=channel_name,
                        msg_id=post.id,
                        offset_id=0,
                        offset_date=None,
                        add_offset=0,
                        limit=100,  # Up to 100 comments per post
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    
                    total_comments += len(comments.messages)
                    
                    # Like each comment
                    for j, comment in enumerate(comments.messages):
                        try:
                            # Like the comment
                            await client(LikeRequest(
                                peer=channel_name,
                                id=comment.id
                            ))
                            
                            liked_comments += 1
                            
                            # Update progress
                            if progress_callback:
                                progress = 50 + int((liked_comments / (total_comments or 1)) * 50)  # Second half for liking
                                progress_callback(
                                    task_id, 
                                    min(progress, 100),
                                    total_comments,
                                    f"Liked {liked_comments}/{total_comments} comments in {target}"
                                )
                            
                            # Check if we've reached the limit
                            if liked_comments >= limit_per_account:
                                logger.info(f"Reached like limit ({limit_per_account}) for task {task_id}")
                                break
                            
                            # Random delay between likes
                            delay = random.randint(delay_min, delay_max)
                            await asyncio.sleep(delay)
                            
                        except FloodWaitError as e:
                            # Handle rate limiting
                            logger.warning(f"FloodWaitError in like_comments: {e}")
                            
                            if progress_callback:
                                progress_callback(
                                    task_id,
                                    None,
                                    None,
                                    f"Rate limited, waiting for {e.seconds} seconds"
                                )
                            
                            await asyncio.sleep(e.seconds)
                            continue
                            
                        except Exception as e:
                            logger.error(f"Error liking comment: {e}")
                            continue
                    
                    # Check if we've reached the limit
                    if liked_comments >= limit_per_account:
                        break
                    
                except Exception as e:
                    logger.error(f"Error getting comments for post {post.id}: {e}")
                    continue
            
            # Update task results
            async with async_session_factory() as session:
                task = await session.get(Task, task_id)
                if task:
                    task.total_items = total_comments
                    task.logs = f"Liked comments: {liked_comments}/{total_comments}"
                    await session.commit()
            
            # Update progress to complete
            if progress_callback:
                progress_callback(
                    task_id, 
                    100, 
                    total_comments,
                    f"Completed liking comments in {target}. Liked: {liked_comments}/{total_comments}"
                )
            
            # Close client session
            await close_client_session(account)
            
            return True
            
        else:
            # Handle direct post link
            # This would require different parsing of the target URL
            logger.error(f"Direct post links not yet supported for like comments task {task_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error processing like comments task {task_id}: {e}")
        
        # Close client session if exists
        if account:
            await close_client_session(account)
            
        return False