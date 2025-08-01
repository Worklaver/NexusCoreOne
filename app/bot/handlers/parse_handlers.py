import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state.state import State, StatesGroup
from aiogram.utils.markdown import hbold, hcode

from app.bot.keyboards.parse_keyboards import (
    get_parse_menu_keyboard,
    get_parse_type_keyboard,
    get_parse_target_keyboard,
    get_parse_options_keyboard,
    get_back_to_parse_keyboard
)
from app.bot.utils.api_client import api_client
from app.database.models import TaskStatus, TaskType

# Configure logging
logger = logging.getLogger(__name__)

# Router
router = Router()

# States for parse flow
class ParseStates(StatesGroup):
    selecting_type = State()
    entering_target = State()
    selecting_options = State()
    confirmation = State()

# Command handler for parse menu
@router.message(Command("parse"))
async def cmd_parse(message: types.Message):
    """Handle /parse command"""
    await show_parse_menu(message)

# Callback handler for opening parse menu
@router.callback_query(F.data == "open_parse_menu")
async def open_parse_menu_callback(callback: types.CallbackQuery):
    """Handle callback to open parse menu"""
    await show_parse_menu(callback.message)
    await callback.answer()

async def show_parse_menu(message: types.Message):
    """Show parse menu with options"""
    menu_text = (
        f"🔍 {hbold('Меню парсинга')}\n\n"
        f"Выберите действие для парсинга данных из Telegram.\n\n"
        f"С помощью парсинга вы можете собирать:\n"
        f"- Участников групп и каналов\n"
        f"- Авторов сообщений в каналах\n"
        f"- Комментаторов под постами\n\n"
        f"Для парсинга необходим минимум один активный аккаунт."
    )
    
    await message.answer(menu_text, reply_markup=get_parse_menu_keyboard())

# Start new parsing process
@router.callback_query(F.data == "start_new_parsing")
async def start_new_parsing(callback: types.CallbackQuery, state: FSMContext):
    """Handle callback to start new parsing process"""
    user_id = callback.from_user.id
    
    try:
        # Check if user has active accounts
        response = await api_client.get(f"/api/accounts?user_id={user_id}&active_only=true")
        accounts = response.json()
        
        if not accounts:
            await callback.message.edit_text(
                "❌ У вас нет активных аккаунтов. Добавьте хотя бы один активный аккаунт для парсинга.",
                reply_markup=get_back_to_parse_keyboard()
            )
            await callback.answer()
            return
        
        # Show parsing types
        await callback.message.edit_text(
            f"📋 {hbold('Выберите тип парсинга:')}\n\n"
            f"👥 Участники - сбор пользователей из групп и каналов\n"
            f"✍️ Авторы - сбор авторов сообщений из каналов\n"
            f"💬 Комментаторы - сбор пользователей, оставивших комментарии под постами",
            reply_markup=get_parse_type_keyboard()
        )
        
        # Save account IDs for later use
        account_ids = [account["id"] for account in accounts]
        await state.update_data(account_ids=account_ids)
        await state.set_state(ParseStates.selecting_type)
        
    except Exception as e:
        logger.error(f"Error in start_new_parsing: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при подготовке к парсингу. Попробуйте позже.",
            reply_markup=get_back_to_parse_keyboard()
        )
    
    await callback.answer()

# Parse type selection handler
@router.callback_query(ParseStates.selecting_type, F.data.startswith("parse_type:"))
async def parse_type_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle selection of parsing type"""
    parse_type = callback.data.split(":")[1]
    
    # Validate parse type
    if parse_type not in ["members", "writers", "commenters"]:
        await callback.message.edit_text(
            "❌ Выбран неверный тип парсинга. Попробуйте еще раз.",
            reply_markup=get_parse_type_keyboard()
        )
        await callback.answer()
        return
    
    # Save parse type
    await state.update_data(parse_type=parse_type)
    
    # Ask for target
    target_type = {
        "members": "группу или канал",
        "writers": "канал",
        "commenters": "пост в канале"
    }[parse_type]
    
    await callback.message.edit_text(
        f"🎯 {hbold('Укажите цель для парсинга')}\n\n"
        f"Введите @username или ссылку на {target_type}, "
        f"из которого нужно собрать данные:",
        reply_markup=get_parse_target_keyboard()
    )
    
    await state.set_state(ParseStates.entering_target)
    await callback.answer()

# Handle target input
@router.message(ParseStates.entering_target)
async def parse_target_input(message: types.Message, state: FSMContext):
    """Handle input of parsing target"""
    target = message.text.strip()
    
    # Basic validation
    if not target or (not target.startswith("@") and not target.startswith("https://t.me/")):
        await message.answer(
            "❌ Неверный формат цели. Введите @username или ссылку на группу/канал/пост:",
            reply_markup=get_parse_target_keyboard()
        )
        return
    
    # Save target
    await state.update_data(target=target)
    
    # Get parse type
    user_data = await state.get_data()
    parse_type = user_data.get("parse_type")
    
    # Show options
    await message.answer(
        f"⚙️ {hbold('Настройки парсинга')}\n\n"
        f"Цель: {hcode(target)}\n\n"
        f"Выберите настройки парсинга:",
        reply_markup=get_parse_options_keyboard(parse_type)
    )
    
    await state.set_state(ParseStates.selecting_options)

# Handle options selection
@router.callback_query(ParseStates.selecting_options, F.data.startswith("parse_limit:"))
async def parse_options_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle selection of parsing options"""
    limit = int(callback.data.split(":")[1])
    
    # Save limit
    await state.update_data(limit=limit)
    
    # Get all data
    user_data = await state.get_data()
    parse_type = user_data.get("parse_type")
    target = user_data.get("target")
    
    # Format parse type for display
    parse_type_display = {
        "members": "участников",
        "writers": "авторов",
        "commenters": "комментаторов"
    }[parse_type]
    
    # Show confirmation
    limit_display = "все (макс. 10000)" if limit == 0 else str(limit)
    confirmation_text = (
        f"✅ {hbold('Подтвердите запуск парсинга')}\n\n"
        f"Тип: {parse_type_display}\n"
        f"Цель: {hcode(target)}\n"
        f"Лимит: {limit_display}\n\n"
        f"Запустить парсинг?"
    )
    
    # Create confirmation keyboard
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Запустить", callback_data="confirm_parsing"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_parsing")
        ]
    ])
    
    await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
    await state.set_state(ParseStates.confirmation)
    await callback.answer()

# Handle parsing confirmation
@router.callback_query(ParseStates.confirmation, F.data == "confirm_parsing")
async def confirm_parsing(callback: types.CallbackQuery, state: FSMContext):
    """Handle parsing confirmation and start parsing"""
    user_id = callback.from_user.id
    user_data = await state.get_data()
    
    try:
        # Map parse type to task type
        task_type = {
            "members": "parse_members",
            "writers": "parse_writers",
            "commenters": "parse_commenters"
        }[user_data.get("parse_type")]
        
        # Prepare task data
        task_data = {
            "user_id": user_id,
            "task_type": task_type,
            "params": {
                "target": user_data.get("target"),
                "limit": user_data.get("limit", 0),
                "account_ids": user_data.get("account_ids", [])
            }
        }
        
        # Create task
        response = await api_client.post("/api/tasks", json=task_data)
        
        if response.status_code == 201:
            task = response.json()
            task_id = task["id"]
            
            await callback.message.edit_text(
                f"✅ {hbold('Задача парсинга создана!')}\n\n"
                f"ID задачи: {hcode(str(task_id))}\n"
                f"Статус: {task['status']}\n\n"
                f"Вы можете отслеживать прогресс в разделе 'Активные задачи'.",
                reply_markup=get_back_to_parse_keyboard()
            )
        else:
            error_data = response.json()
            await callback.message.edit_text(
                f"❌ Ошибка при создании задачи: {error_data.get('detail', 'Неизвестная ошибка')}",
                reply_markup=get_back_to_parse_keyboard()
            )
    except Exception as e:
        logger.error(f"Error creating parsing task: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании задачи парсинга. Попробуйте позже.",
            reply_markup=get_back_to_parse_keyboard()
        )
    
    # Clear state
    await state.clear()
    await callback.answer()

# Cancel parsing
@router.callback_query(F.data == "cancel_parsing")
async def cancel_parsing(callback: types.CallbackQuery, state: FSMContext):
    """Cancel parsing process"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Парсинг отменен.",
        reply_markup=get_back_to_parse_keyboard()
    )
    await callback.answer()

# View active tasks
@router.callback_query(F.data == "view_active_tasks")
async def view_active_tasks(callback: types.CallbackQuery):
    """View active parsing tasks"""
    user_id = callback.from_user.id
    
    try:
        # Get active tasks
        response = await api_client.get(
            "/api/tasks", 
            params={"user_id": user_id, "status": "running"}
        )
        tasks = response.json()
        
        if tasks:
            tasks_text = f"📊 {hbold('Активные задачи парсинга:')}\n\n"
            
            for task in tasks:
                task_type_display = {
                    "parse_members": "Участники",
                    "parse_writers": "Авторы",
                    "parse_commenters": "Комментаторы"
                }.get(task["task_type"], task["task_type"])
                
                tasks_text += (
                    f"ID: {hcode(str(task['id']))}\n"
                    f"Тип: {task_type_display}\n"
                    f"Прогресс: {task['progress']}%\n"
                    f"Создана: {task['created_at']}\n\n"
                )
                
                if len(tasks_text) > 3500:  # Telegram message limit
                    tasks_text += "... и другие задачи"
                    break
            
            # Add button to cancel tasks
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="❌ Отменить задачу", callback_data="select_task_to_cancel")
                ],
                [
                    types.InlineKeyboardButton(text="🔙 Назад", callback_data="open_parse_menu")
                ]
            ])
            
            await callback.message.edit_text(tasks_text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(
                "📊 У вас нет активных задач парсинга.",
                reply_markup=get_back_to_parse_keyboard()
            )
    except Exception as e:
        logger.error(f"Error viewing active tasks: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении списка активных задач. Попробуйте позже.",
            reply_markup=get_back_to_parse_keyboard()
        )
    
    await callback.answer()

# View databases
@router.callback_query(F.data == "my_databases")
async def view_databases(callback: types.CallbackQuery):
    """View parsed databases"""
    user_id = callback.from_user.id
    
    try:
        # Get completed tasks
        response = await api_client.get(
            "/api/tasks", 
            params={"user_id": user_id, "status": "completed"}
        )
        tasks = response.json()
        
        if tasks:
            # Filter parsing tasks only
            parsing_tasks = [
                task for task in tasks 
                if task["task_type"] in ["parse_members", "parse_writers", "parse_commenters"]
            ]
            
            if parsing_tasks:
                databases_text = f"🗄️ {hbold('Ваши базы данных:')}\n\n"
                
                for task in parsing_tasks:
                    task_type_display = {
                        "parse_members": "Участники",
                        "parse_writers": "Авторы",
                        "parse_commenters": "Комментаторы"
                    }.get(task["task_type"], task["task_type"])
                    
                    target = task["params"].get("target", "Неизвестно")
                    
                    databases_text += (
                        f"ID: {hcode(str(task['id']))}\n"
                        f"Тип: {task_type_display}\n"
                        f"Цель: {target}\n"
                        f"Собрано: {task['total_items']} записей\n"
                        f"Дата: {task['completed_at']}\n\n"
                    )
                    
                    if len(databases_text) > 3500:  # Telegram message limit
                        databases_text += "... и другие базы"
                        break
                
                # Add buttons to view details and export
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                    [
                        types.InlineKeyboardButton(text="📥 Экспорт", callback_data="select_database_to_export")
                    ],
                    [
                        types.InlineKeyboardButton(text="🗑️ Удалить", callback_data="select_database_to_delete")
                    ],
                    [
                        types.InlineKeyboardButton(text="🔙 Назад", callback_data="open_parse_menu")
                    ]
                ])
                
                await callback.message.edit_text(databases_text, reply_markup=keyboard)
            else:
                await callback.message.edit_text(
                    "🗄️ У вас нет сохраненных баз данных парсинга.",
                    reply_markup=get_back_to_parse_keyboard()
                )
        else:
            await callback.message.edit_text(
                "🗄️ У вас нет сохраненных баз данных парсинга.",
                reply_markup=get_back_to_parse_keyboard()
            )
    except Exception as e:
        logger.error(f"Error viewing databases: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении списка баз данных. Попробуйте позже.",
            reply_markup=get_back_to_parse_keyboard()
        )
    
    await callback.answer()

# Back to parse menu
@router.callback_query(F.data == "back_to_parse_menu")
async def back_to_parse_menu(callback: types.CallbackQuery, state: FSMContext = None):
    """Return to parse menu"""
    if state:
        await state.clear()
    
    await show_parse_menu(callback.message)
    await callback.answer()