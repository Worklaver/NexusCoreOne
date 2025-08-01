import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state.state import State, StatesGroup
from aiogram.utils.markdown import hbold, hcode

from app.bot.keyboards.like_keyboards import (
    get_like_menu_keyboard,
    get_like_target_keyboard,
    get_like_options_keyboard,
    get_back_to_like_keyboard
)
from app.bot.utils.api_client import api_client
from app.database.models import TaskStatus

# Configure logging
logger = logging.getLogger(__name__)

# Router
router = Router()

# States
class LikeStates(StatesGroup):
    entering_target = State()
    selecting_options = State()
    confirmation = State()

# Command handler
@router.message(Command("like"))
async def cmd_like(message: types.Message):
    """Handle /like command"""
    await show_like_menu(message)

# Callback handler for opening like menu
@router.callback_query(F.data == "open_like_menu")
async def open_like_menu_callback(callback: types.CallbackQuery):
    """Handle callback to open like menu"""
    await show_like_menu(callback.message)
    await callback.answer()

async def show_like_menu(message: types.Message):
    """Show like menu with options"""
    menu_text = (
        f"❤️ {hbold('Меню лайкинга комментариев')}\n\n"
        f"Выберите действие для лайкинга комментариев в Telegram.\n\n"
        f"С помощью лайкинга вы можете автоматически ставить лайки на комментарии "
        f"под постами в каналах, что помогает повысить активность и видимость.\n\n"
        f"Для лайкинга необходим минимум один активный аккаунт."
    )
    
    await message.answer(menu_text, reply_markup=get_like_menu_keyboard())

# Start new like process
@router.callback_query(F.data == "start_new_like")
async def start_new_like(callback: types.CallbackQuery, state: FSMContext):
    """Handle callback to start new like process"""
    user_id = callback.from_user.id
    
    try:
        # Check if user has active accounts
        response = await api_client.get(f"/api/accounts?user_id={user_id}&active_only=true")
        accounts = response.json()
        
        if not accounts:
            await callback.message.edit_text(
                "❌ У вас нет активных аккаунтов. Добавьте хотя бы один активный аккаунт для лайкинга.",
                reply_markup=get_back_to_like_keyboard()
            )
            await callback.answer()
            return
        
        # Ask for target
        await callback.message.edit_text(
            f"🎯 {hbold('Укажите цель для лайкинга комментариев')}\n\n"
            f"Введите @username канала или ссылку на пост, под которым нужно лайкать комментарии:",
            reply_markup=get_like_target_keyboard()
        )
        
        # Save account IDs for later use
        account_ids = [account["id"] for account in accounts]
        await state.update_data(account_ids=account_ids)
        await state.set_state(LikeStates.entering_target)
        
    except Exception as e:
        logger.error(f"Error in start_new_like: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при подготовке к лайкингу. Попробуйте позже.",
            reply_markup=get_back_to_like_keyboard()
        )
    
    await callback.answer()

# Target input handler
@router.message(LikeStates.entering_target)
async def like_target_input(message: types.Message, state: FSMContext):
    """Handle input of like target"""
    target = message.text.strip()
    
    # Basic validation
    if not target or (not target.startswith("@") and not target.startswith("https://t.me/")):
        await message.answer(
            "❌ Неверный формат цели. Введите @username канала или ссылку на пост:",
            reply_markup=get_like_target_keyboard()
        )
        return
    
    # Save target
    await state.update_data(target=target)
    
    # Show options
    await message.answer(
        f"⚙️ {hbold('Настройки лайкинга')}\n\n"
        f"Цель: {hcode(target)}\n\n"
        f"Выберите настройки лайкинга комментариев:",
        reply_markup=get_like_options_keyboard()
    )
    
    await state.set_state(LikeStates.selecting_options)

# Options selection handler
@router.callback_query(LikeStates.selecting_options, F.data.startswith("like_options:"))
async def like_options_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle selection of like options"""
    options = callback.data.split(":")[1].split(",")
    
    # Parse options
    delay_min = int(options[0])
    delay_max = int(options[1])
    limit_per_account = int(options[2])
    
    # Save options
    await state.update_data(
        delay_min=delay_min,
        delay_max=delay_max,
        limit_per_account=limit_per_account
    )
    
    # Get target for confirmation
    user_data = await state.get_data()
    target = user_data.get("target")
    
    # Show confirmation
    confirmation_text = (
        f"✅ {hbold('Подтвердите запуск лайкинга комментариев')}\n\n"
        f"Цель: {hcode(target)}\n"
        f"Задержка: {delay_min}-{delay_max} сек.\n"
        f"Лимит на аккаунт: {limit_per_account}\n\n"
        f"Запустить лайкинг комментариев?"
    )
    
    # Create confirmation keyboard
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Запустить", callback_data="confirm_like"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_like")
        ]
    ])
    
    await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
    await state.set_state(LikeStates.confirmation)
    await callback.answer()

# Confirmation handler
@router.callback_query(LikeStates.confirmation, F.data == "confirm_like")
async def confirm_like(callback: types.CallbackQuery, state: FSMContext):
    """Handle like confirmation and start liking"""
    user_id = callback.from_user.id
    user_data = await state.get_data()
    
    try:
        # Prepare task data
        task_data = {
            "user_id": user_id,
            "task_type": "like_comments",
            "params": {
                "target": user_data.get("target"),
                "delay_min": user_data.get("delay_min", 5),
                "delay_max": user_data.get("delay_max", 15),
                "limit_per_account": user_data.get("limit_per_account", 100),
                "account_ids": user_data.get("account_ids", [])
            }
        }
        
        # Create task
        response = await api_client.post("/api/tasks", json=task_data)
        
        if response.status_code == 201:
            task = response.json()
            task_id = task["id"]
            
            await callback.message.edit_text(
                f"✅ {hbold('Задача лайкинга комментариев создана!')}\n\n"
                f"ID задачи: {hcode(str(task_id))}\n"
                f"Статус: {task['status']}\n\n"
                f"Вы можете отслеживать прогресс в разделе 'Активные задачи'.",
                reply_markup=get_back_to_like_keyboard()
            )
        else:
            error_data = response.json()
            await callback.message.edit_text(
                f"❌ Ошибка при создании задачи: {error_data.get('detail', 'Неизвестная ошибка')}",
                reply_markup=get_back_to_like_keyboard()
            )
    except Exception as e:
        logger.error(f"Error creating like task: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании задачи лайкинга. Попробуйте позже.",
            reply_markup=get_back_to_like_keyboard()
        )
    
    # Clear state
    await state.clear()
    await callback.answer()

# Cancel liking
@router.callback_query(F.data == "cancel_like")
async def cancel_like(callback: types.CallbackQuery, state: FSMContext):
    """Cancel liking process"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Лайкинг отменен.",
        reply_markup=get_back_to_like_keyboard()
    )
    await callback.answer()

# View active like tasks
@router.callback_query(F.data == "view_active_likes")
async def view_active_likes(callback: types.CallbackQuery):
    """View active like tasks"""
    user_id = callback.from_user.id
    
    try:
        # Get active like tasks
        response = await api_client.get(
            "/api/tasks", 
            params={"user_id": user_id, "status": "running", "task_type": "like_comments"}
        )
        tasks = response.json()
        
        if tasks:
            tasks_text = f"📊 {hbold('Активные задачи лайкинга:')}\n\n"
            
            for task in tasks:
                target = task["params"].get("target", "Неизвестно")
                
                tasks_text += (
                    f"ID: {hcode(str(task['id']))}\n"
                    f"Цель: {target}\n"
                    f"Прогресс: {task['progress']}%\n"
                    f"Создана: {task['created_at']}\n\n"
                )
                
                if len(tasks_text) > 3500:  # Telegram message limit
                    tasks_text += "... и другие задачи"
                    break
            
            # Add button to cancel tasks
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="❌ Отменить задачу", callback_data="select_like_to_cancel")
                ],
                [
                    types.InlineKeyboardButton(text="🔙 Назад", callback_data="open_like_menu")
                ]
            ])
            
            await callback.message.edit_text(tasks_text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(
                "📊 У вас нет активных задач лайкинга комментариев.",
                reply_markup=get_back_to_like_keyboard()
            )
    except Exception as e:
        logger.error(f"Error viewing active like tasks: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении списка активных задач лайкинга. Попробуйте позже.",
            reply_markup=get_back_to_like_keyboard()
        )
    
    await callback.answer()

# Back to like menu
@router.callback_query(F.data == "back_to_like_menu")
async def back_to_like_menu(callback: types.CallbackQuery, state: FSMContext = None):
    """Return to like menu"""
    if state:
        await state.clear()
    
    await show_like_menu(callback.message)
    await callback.answer()