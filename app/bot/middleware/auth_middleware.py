from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TGUser
from sqlalchemy import select
import logging

from app.database.models import User
from app.database.db_session import async_session_factory

# Configure logging
logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    """Middleware to handle user authentication and registration"""
    
    async def __call__(
        self, 
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process incoming event and ensure user is registered in database
        
        Args:
            handler: Event handler function
            event: Event from Telegram
            data: Data from previous middlewares
            
        Returns:
            Result of handler function
        """
        # Extract user from update
        if "event_from_user" in data:
            telegram_user: TGUser = data["event_from_user"]
            
            # Ensure user exists in database
            try:
                db_user = await self._get_or_create_user(
                    telegram_id=str(telegram_user.id),
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name
                )
                
                # Add user to data dict for handlers
                data["bot_user"] = db_user
                
            except Exception as e:
                logger.error(f"Error in auth middleware: {e}")
        
        # Call the handler
        return await handler(event, data)
    
    async def _get_or_create_user(self, telegram_id, username, first_name, last_name):
        """
        Get existing user or create a new one
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            
        Returns:
            User: User model instance
        """
        async with async_session_factory() as session:
            # Try to find existing user
            query = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                # Update user info if needed
                changed = False
                
                if username and user.username != username:
                    user.username = username
                    changed = True
                
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    changed = True
                
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    changed = True
                
                if changed:
                    await session.commit()
                    await session.refresh(user)
                
                return user
            else:
                # Create new user
                new_user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    role="user"
                )
                
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                
                # Also create default settings for the user
                from app.database.models import Settings
                default_settings = Settings(user_id=new_user.id)
                session.add(default_settings)
                await session.commit()
                
                logger.info(f"Created new user: {telegram_id} ({username or first_name})")
                return new_user