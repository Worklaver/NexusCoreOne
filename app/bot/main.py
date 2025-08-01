import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from dotenv import load_dotenv

from app.bot.handlers import (
    account_handlers, 
    task_handlers, 
    settings_handlers, 
    parse_handlers, 
    invite_handlers, 
    like_handlers
)
from app.bot.middleware.auth_middleware import AuthMiddleware
from app.database.db_session import init_models

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Router for basic commands
main_router = Router()

@main_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Handle /start command - introduce the bot and show main menu
    """
    from app.bot.keyboards.main_keyboard import get_main_menu_keyboard
    
    await message.answer(
        f"👋 Привет, {hbold(message.from_user.first_name)}!\n\n"
        f"Добро пожаловать в 🤖 NexusCore - многофункционального Telegram бота для парсинга, "
        f"инвайтинга и управления аккаунтами.\n\n"
        f"Выберите нужный раздел из меню ниже:",
        reply_markup=get_main_menu_keyboard()
    )

@main_router.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """
    Handle /help command - show available commands
    """
    help_text = (
        f"🔍 {hbold('Доступные команды:')}\n\n"
        f"/start - Запустить бота и показать главное меню\n"
        f"/accounts - Управление аккаунтами\n"
        f"/parse - Меню парсинга\n"
        f"/invite - Меню инвайтинга\n"
        f"/like - Меню лайкинга комментариев\n"
        f"/tasks - Активные задачи и результаты\n"
        f"/settings - Настройки бота\n"
        f"/help - Показать это сообщение"
    )
    
    await message.answer(help_text)

async def main():
    """
    Main function to start the bot
    """
    # Initialize database
    await init_models()
    
    # Get token from env
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set in environment variables")
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    
    # Register middleware
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Register routers
    dp.include_router(main_router)
    dp.include_router(account_handlers.router)
    dp.include_router(task_handlers.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(parse_handlers.router)
    dp.include_router(invite_handlers.router)
    dp.include_router(like_handlers.router)
    
    # Start polling
    logger.info("Starting NexusCore bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")