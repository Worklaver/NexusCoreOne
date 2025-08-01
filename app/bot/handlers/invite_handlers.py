import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state.state import State, StatesGroup
from aiogram.utils.markdown import hbold, hcode

from app.bot.keyboards.invite_keyboards import (
    get_invite_menu_keyboard,
    get_invite_source_keyboard,
    get_invite_target_keyboard,
    get_invite_options_keyboard,
    get_back_to_invite_keyboard
)
from app.bot.utils.api_client import api_client
from app.database.models import TaskStatus

# Configure logging
logger = logging.getLogger(__name__)

# Router
router = Router()

# States
class InviteStates(StatesGroup):
    selecting_source = State()
    entering_source = State()
    entering_target = State()
    selecting_options = State()
    confirmation = State()

# Command handler
@router.message(Command("invite"))
async def cmd_invite(message: types.Message):
    """Handle /invite command"""
    await show_invite_menu(message)

# Callback handler for opening invite menu
@router.callback_query(F.data == "open_invite_menu")
async def open_invite_menu_callback(callback: types.CallbackQuery):
    """Handle callback to open invite menu"""
    await show_invite_menu(callback.message)
    await callback.answer()

async def show_invite_menu(message: types.Message):
    """Show invite menu with options"""
    menu_text = (
        f"➕ {hbold('Меню инвайтинга')}\n\n"
        f"Выберите действие для инвайтинга пользователей.\n\n"
        f"С помощью инвайтинга вы можете приглашать пользователей в свои группы и каналы, "
        f"используя данные из ваших баз или внешних источников.\n\n"
        f"Для инвайтинга необходим минимум один активный аккаунт."
    )
    
    await message.answer(menu_text, reply_markup=get_invite_menu_keyboard())

# Start new invite process
@router.callback_query(F.data == "start_new_invite")
async def start_new_invite(callback: types.CallbackQuery, state: FSMContext):
    """Handle callback to start new invite process"""
    user_id = callback.from_user.id
    
    try:
        # Check if user has active accounts
        response = await api_client.get(f"/api/accounts?user_id={user_id}&active_only=true")
        accounts = response.json()
        
        if not accounts:
            await callback.message.edit_text(
                "❌ У вас нет активных аккаунтов. Добавьте хотя бы один активный аккаунт для инвайтинга.",
                reply_markup=get_back_to_invite_keyboard()
            )
            await callback.answer()
            return
            
        # Show source selection
        await callback.message.edit_text(
            f"📋 {hbold('Выберите источник пользователей для инвайтинга:')}\n\n"
            f"Вы можете использовать базу данных из парсинга или указать внешний источник.",
            reply_markup=get_invite_source_keyboard()
        )
        
        # Save account IDs for later use
        account_ids = [account["id"] for account in accounts]
        await state.update_data(account_ids=account_ids)
        await state.set_state(InviteStates.selecting_source)
        
    except Exception as e:
        logger.error(f"Error in start_new_invite: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при подготовке к инвайтингу. Попробуйте позже.",
            reply_markup=get_back_to_invite_keyboard()
        )
    
    await callback.answer()

# Source selection handler
@router.callback_query(InviteStates.selecting_source, F.data.startswith("invite_source:"))
async def invite_source_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle selection of invite source"""
    source_type = callback.data.split(":")[1]
    
    # Validate source type
    if source_type not in ["database", "external"]:
        await callback.message.edit_text(
            "❌ Выбран неверный источник. Попробуйте еще раз.",
            reply_markup=get_invite_source_keyboard()
        )
        await callback.answer()
        return
    
    # Save source type
    await state.update_data(source_type=source_type)
    
    if source_type == "database":
        # Show available databases
        try:
            user_id = callback.from_user.id
            response = await api_client.get(
                "/api/tasks", 
                params={"user_id": user_id, "status": "completed", "task_type": "parse_members"}
            )
            tasks = response.json()
            
            if tasks:
                # Create keyboard with databases
                keyboard = []
                
                for task in tasks:
                    target = task["params"].get("target", "Неизвестно")
                    keyboard.append([
                        types.InlineKeyboardButton(
                            text=f"{target} ({task['total_items']} записей)",
                            callback_data=f"invite_db_source:{task['id']}"
                        )
                    ])
                
                # Add cancel button
                keyboard.append([
                    types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_invite")
                ])
                
                await callback.message.edit_text(
                    f"📊 {hbold('Выберите базу данных для инвайтинга:')}\n\n"
                    f"Выберите базу с пользователями, которых нужно пригласить:",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
            else:
                await callback.message.edit_text(
                    "❌ У вас нет доступных баз данных с пользователями. Сначала выполните парсинг участников.",
                    reply_markup=get_back_to_invite_keyboard()
                )
        except Exception as e:
            logger.error(f"Error getting databases: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при получении списка баз данных. Попробуйте позже.",
                reply_markup=get_back_to_invite_keyboard()
            )
    else:
        # Ask for external source
        await callback.message.edit_text(
            f"📝 {hbold('Укажите внешний источник пользователей')}\n\n"
            f"Введите список пользователей для инвайтинга (по одному имени пользователя на строку).\n"
            f"Можно указывать @username или ссылки на пользователей.",
            reply_markup=get_invite_target_keyboard()
        )
        await state.set_state(InviteStates.entering_source)
    
    await callback.answer()

# Database source selection handler
@router.callback_query(F.data.startswith("invite_db_source:"))
async def invite_db_source_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle selection of database source"""
    db_id = int(callback.data.split(":")[1])
    
    # Save database ID
    await state.update_data(source_db_id=db_id)
    
    # Ask for target
    await callback.message.edit_text(
        f"🎯 {hbold('Укажите цель для инвайтинга')}\n\n"
        f"Введите @username или ссылку на группу/канал, куда нужно пригласить пользователей:",
        reply_markup=get_invite_target_keyboard()
    )
    
    await state.set_state(InviteStates.entering_target)
    await callback.answer()

# External source input handler
@router.message(InviteStates.entering_source)
async def invite_external_source_input(message: types.Message, state: FSMContext):
    """Handle input of external invite source"""
    source = message.text.strip()
    
    # Basic validation
    if not source or len(source) < 3:
        await message.answer(
            "❌ Слишком короткий список пользователей. Пожалуйста, введите список пользователей (по одному на строку):",
            reply_markup=get_invite_target_keyboard()
        )
        return
    
    # Parse usernames
    usernames = [line.strip() for line in source.split("\n") if line.strip()]
    
    # Validate usernames
    if not usernames:
        await message.answer(
            "❌ Не удалось распознать список пользователей. Пожалуйста, введите список пользователей (по одному на строку):",
            reply_markup=get_invite_target_keyboard()
        )
        return
    
    # Save usernames
    await state.update_data(usernames=usernames)
    
    # Ask for target
    await message.answer(
        f"🎯 {hbold('Укажите цель для инвайтинга')}\n\n"
        f"Введите @username или ссылку на группу/канал, куда нужно пригласить пользователей:",
        reply_markup=get_invite_target_keyboard()
    )
    
    await state.set_state(InviteStates.entering_target)

# Target input handler
@router.message(InviteStates.entering_target)
async def invite_target_input(message: types.Message, state: FSMContext):
    """Handle input of invite target"""
    target = message.text.strip()
    
    # Basic validation
    if not target or (not target.startswith("@") and not target.startswith("https://t.me/")):
        await message.answer(
            "❌ Неверный формат цели. Введите @username или ссылку на группу/канал:",
            reply_markup=get_invite_target_keyboard()
        )
        return
    
    # Save target
    await state.update_data(target=target)
    
    # Show options
    await message.answer(
        f"⚙️ {hbold('Настройки инвайтинга')}\n\n"
        f"Цель: {hcode(target)}\n\n"
        f"Выберите настройки инвайтинга:",
        reply_markup=get_invite_options_keyboard()
    )
    
    await state.set_state(InviteStates.selecting_options)

# Options selection handler
@router.callback_query(InviteStates.selecting_options, F.data.startswith("invite_options:"))
async def invite_options_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle selection of invite options"""
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
    
    # Get all data for confirmation
    user_data = await state.get_data()
    target = user_data.get("target")
    
    # Format source for display
    if user_data.get("source_type") == "database":
        source_text = f"База данных (ID: {user_data.get('source_db_id')})"
    else:
        usernames = user_data.get("usernames", [])
        count = len(usernames)
        source_text = f"Внешний список ({count} пользователей)"
    
    # Show confirmation
    confirmation_text = (
        f"✅ {hbold('Подтвердите запуск инвайтинга')}\n\n"
        f"Источник: {source_text}\n"
        f"Цель: {hcode(target)}\n"
        f"Задержка: {delay_min}-{delay_max} сек.\n"
        f"Лимит на аккаунт: {limit_per_account}\n\n"
        f"Запустить инвайтинг?"
    )
    
    # Create confirmation keyboard
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Запустить", callback_data="confirm_invite"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_invite")
        ]
    ])
    
    await callback.message.edit_text(confirmation_text, reply_markup=keyboard)
    await state.set_state(InviteStates.confirmation)
    await callback.answer()

# Confirmation handler
@router.callback_query(InviteStates.confirmation, F.data == "confirm_invite")
async def confirm_invite(callback: types.CallbackQuery, state: FSMContext):
    """Handle invite confirmation and start invite"""
    user_id = callback.from_user.id
    user_data = await state.get_data()
    
    try:
        # Prepare task data
        task_data = {
            "user_id": user_id,
            "task_type": "invite_users",
            "params": {
                "target": user_data.get("target"),
                "delay_min": user_data.get("delay_min", 30),
                "delay_max": user_data.get("delay_max", 60),
                "limit_per_account": user_data.get("limit_per_account", 50),
                "account_ids": user_data.get("account_ids", [])
            }
        }
        
        # Add source-specific parameters
        if user_data.get("source_type") == "database":
            task_data["params"]["source_db_id"] = user_data.get("source_db_id")
        else:
            task_data["params"]["usernames"] = user_data.get("usernames", [])
        
        # Create task
        response = await api_client.post("/api/tasks", json=task_data)
        
        if response.status_code == 201:
            task = response.json()
            task_id = task["id"]
            
            await callback.message.edit_text(
                f"✅ {hbold('Задача инвайтинга создана!')}\n\n"
                f"ID задачи: {hcode(str(task_id))}\n"
                f"Статус: {task['status']}\n\n"
                f"Вы можете отслеживать прогресс в разделе 'Активные задачи'.",
                reply_markup=get_back_to_invite_keyboard()
            )
        else:
            error_data = response.json()
            await callback.message.edit_text(
                f"❌ Ошибка при создании задачи: {error_data.get('detail', 'Неизвестная ошибка')}",
                reply_markup=get_back_to_invite_keyboard()
            )
    except Exception as e:
        logger.error(f"Error creating invite task: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании задачи инвайтинга. Попробуйте позже.",
            reply_markup=get_back_to_invite_keyboard()
        )
    
    # Clear state
    await state.clear()
    await callback.answer()

# Cancel invite
@router.callback_query(F.data == "cancel_invite")
async def cancel_invite(callback: types.CallbackQuery, state: FSMContext):
    """Cancel invite process"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Инвайтинг отменен.",
        reply_markup=get_back_to_invite_keyboard()
    )
    await callback.answer()

# View active invite tasks
@router.callback_query(F.data == "view_active_invites")
async def view_active_invites(callback: types.CallbackQuery):
    """View active invite tasks"""
    user_id = callback.from_user.id
    
    try:
        # Get active invite tasks
        response = await api_client.get(
            "/api/tasks", 
            params={"user_id": user_id, "status": "running", "task_type": "invite_users"}
        )
        tasks = response.json()
        
        if tasks:
            tasks_text = f"📊 {hbold('Активные задачи инвайтинга:')}\n\n"
            
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
                    types.InlineKeyboardButton(text="❌ Отменить задачу", callback_data="select_invite_to_cancel")
                ],
                [
                    types.InlineKeyboardButton(text="🔙 Назад", callback_data="open_invite_menu")
                ]
            ])
            
            await callback.message.edit_text(tasks_text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(
                "📊 У вас нет активных задач инвайтинга.",
                reply_markup=get_back_to_invite_keyboard()
            )
    except Exception as e:
        logger.error(f"Error viewing active invite tasks: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении списка активных задач инвайтинга. Попробуйте позже.",
            reply_markup=get_back_to_invite_keyboard()
        )
    
    await callback.answer()

# Back to invite menu
@router.callback_query(F.data == "back_to_invite_menu")
async def back_to_invite_menu(callback: types.CallbackQuery, state: FSMContext = None):
    """Return to invite menu"""
    if state:
        await state.clear()
    
    await show_invite_menu(callback.message)
    await callback.answer()