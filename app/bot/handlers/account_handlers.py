import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state.state import State, StatesGroup
from aiogram.utils.markdown import hbold, hcode

from app.bot.keyboards.account_keyboards import (
    get_accounts_menu_keyboard,
    get_account_detail_keyboard,
    get_add_account_cancel_keyboard,
    get_back_to_accounts_keyboard
)
from app.bot.utils.api_client import api_client
from app.database.models import AccountStatus

# Configure logging
logger = logging.getLogger(__name__)

# Router
router = Router()

# States
class AddAccountStates(StatesGroup):
    phone = State()
    api_id = State()
    api_hash = State()
    confirmation = State()

# Command handler
@router.message(Command("accounts"))
async def cmd_accounts(message: types.Message):
    """Handle /accounts command"""
    await show_accounts_menu(message)

# Callback handler for accounts menu button
@router.callback_query(F.data == "open_accounts_menu")
async def accounts_menu_callback(callback: types.CallbackQuery):
    """Handle callback from main menu to accounts menu"""
    await show_accounts_menu(callback.message)
    await callback.answer()

async def show_accounts_menu(message: types.Message):
    """Show accounts menu with list of accounts"""
    user_id = message.from_user.id
    
    try:
        # Get accounts from API
        response = await api_client.get(f"/api/accounts?user_id={user_id}")
        accounts = response.json()
        
        if accounts:
            # Format accounts list
            accounts_text = (
                f"👤 {hbold('Ваши аккаунты:')}\n\n"
            )
            
            for idx, account in enumerate(accounts, 1):
                status_emoji = {
                    "active": "✅",
                    "cooling_down": "⏳",
                    "banned": "🚫",
                    "needs_verification": "⚠️",
                    "limited": "⚠️",
                    "inactive": "❌"
                }.get(account["status"], "❓")
                
                accounts_text += (
                    f"{idx}. {status_emoji} {hcode(account['phone'])}\n"
                )
            
            await message.answer(
                accounts_text,
                reply_markup=get_accounts_menu_keyboard(accounts)
            )
        else:
            await message.answer(
                "🔍 У вас пока нет добавленных аккаунтов. Добавьте аккаунт, чтобы начать работу.",
                reply_markup=get_accounts_menu_keyboard([])
            )
    except Exception as e:
        logger.error(f"Error retrieving accounts: {e}")
        await message.answer(
            "❌ Произошла ошибка при получении списка аккаунтов. Попробуйте позже.",
            reply_markup=get_back_to_accounts_keyboard()
        )

# Account details handler
@router.callback_query(F.data.startswith("account_details:"))
async def account_details_callback(callback: types.CallbackQuery):
    """Handle callback to show account details"""
    account_id = int(callback.data.split(":")[1])
    
    try:
        # Get account details from API
        response = await api_client.get(f"/api/accounts/{account_id}")
        account = response.json()
        
        # Get status emoji
        status_emoji = {
            "active": "✅",
            "cooling_down": "⏳",
            "banned": "🚫",
            "needs_verification": "⚠️",
            "limited": "⚠️",
            "inactive": "❌"
        }.get(account["status"], "❓")
        
        # Format account details
        cooldown_text = ""
        if account["status"] == "cooling_down" and account["cooldown_until"]:
            cooldown_text = f"\n⏳ В отлежке до: {account['cooldown_until']}"
        
        usage_text = (
            f"📊 {hbold('Использовано сегодня:')}\n"
            f"- Парсинг: {account['daily_parse_count']}\n"
            f"- Инвайтинг: {account['daily_invite_count']}\n"
            f"- Лайкинг: {account['daily_like_count']}"
        )
        
        account_text = (
            f"📱 {hbold('Аккаунт:')} {hcode(account['phone'])}\n"
            f"🔑 API ID: {hcode(account['api_id'])}\n"
            f"📶 Статус: {status_emoji} {account['status'].upper()}"
            f"{cooldown_text}\n\n"
            f"{usage_text}"
        )
        
        await callback.message.edit_text(
            account_text,
            reply_markup=get_account_detail_keyboard(account_id)
        )
    except Exception as e:
        logger.error(f"Error retrieving account details: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении информации об аккаунте.",
            reply_markup=get_back_to_accounts_keyboard()
        )
    
    await callback.answer()

# Add account handler
@router.callback_query(F.data == "add_account")
async def add_account_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle callback to add a new account"""
    await callback.message.edit_text(
        "📱 Введите номер телефона аккаунта в международном формате (например, +79123456789):",
        reply_markup=get_add_account_cancel_keyboard()
    )
    await state.set_state(AddAccountStates.phone)
    await callback.answer()

# Phone number handler
@router.message(AddAccountStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Handle phone number input"""
    phone = message.text.strip()
    
    # Basic validation
    if not phone.startswith("+") or not phone[1:].isdigit():
        await message.answer(
            "❌ Неверный формат номера. Введите номер в международном формате (например, +79123456789):",
            reply_markup=get_add_account_cancel_keyboard()
        )
        return
    
    await state.update_data(phone=phone)
    await message.answer(
        "🔑 Введите API ID для этого аккаунта (получите на my.telegram.org):",
        reply_markup=get_add_account_cancel_keyboard()
    )
    await state.set_state(AddAccountStates.api_id)

# API ID handler
@router.message(AddAccountStates.api_id)
async def process_api_id(message: types.Message, state: FSMContext):
    """Handle API ID input"""
    api_id = message.text.strip()
    
    # Basic validation
    if not api_id.isdigit():
        await message.answer(
            "❌ API ID должен содержать только цифры. Попробуйте еще раз:",
            reply_markup=get_add_account_cancel_keyboard()
        )
        return
    
    await state.update_data(api_id=api_id)
    await message.answer(
        "🔐 Введите API Hash для этого аккаунта (получите на my.telegram.org):",
        reply_markup=get_add_account_cancel_keyboard()
    )
    await state.set_state(AddAccountStates.api_hash)

# API Hash handler
@router.message(AddAccountStates.api_hash)
async def process_api_hash(message: types.Message, state: FSMContext):
    """Handle API Hash input"""
    api_hash = message.text.strip()
    
    # Basic validation (API hash is 32 hex characters)
    if len(api_hash) != 32 or not all(c in "0123456789abcdefABCDEF" for c in api_hash):
        await message.answer(
            "❌ Неверный формат API Hash. API Hash должен быть 32-символьной строкой. Попробуйте еще раз:",
            reply_markup=get_add_account_cancel_keyboard()
        )
        return
    
    # Get all data
    user_data = await state.update_data(api_hash=api_hash)
    
    # Show confirmation message
    confirmation_text = (
        f"📱 {hbold('Проверьте данные аккаунта:')}\n\n"
        f"Номер: {hcode(user_data['phone'])}\n"
        f"API ID: {hcode(user_data['api_id'])}\n"
        f"API Hash: {hcode(user_data['api_hash'][:5] + '...' + user_data['api_hash'][-5:])}\n\n"
        f"Подтверждаете добавление аккаунта?"
    )
    
    # Create confirmation keyboard
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_add_account"),
            types.InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_add_account")
        ]
    ])
    
    await message.answer(confirmation_text, reply_markup=keyboard)
    await state.set_state(AddAccountStates.confirmation)

# Confirmation handler
@router.callback_query(AddAccountStates.confirmation, F.data == "confirm_add_account")
async def confirm_add_account(callback: types.CallbackQuery, state: FSMContext):
    """Handle account addition confirmation"""
    user_data = await state.get_data()
    user_id = callback.from_user.id
    
    try:
        # Send data to API
        account_data = {
            "user_id": user_id,
            "phone": user_data["phone"],
            "api_id": user_data["api_id"],
            "api_hash": user_data["api_hash"]
        }
        
        response = await api_client.post("/api/accounts", json=account_data)
        
        if response.status_code == 201:
            await callback.message.edit_text(
                "✅ Аккаунт успешно добавлен! Теперь вы можете использовать его для парсинга и инвайтинга.",
                reply_markup=get_back_to_accounts_keyboard()
            )
        else:
            error_data = response.json()
            await callback.message.edit_text(
                f"❌ Ошибка при добавлении аккаунта: {error_data.get('detail', 'Неизвестная ошибка')}",
                reply_markup=get_back_to_accounts_keyboard()
            )
    except Exception as e:
        logger.error(f"Error adding account: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при добавлении аккаунта. Попробуйте позже.",
            reply_markup=get_back_to_accounts_keyboard()
        )
    
    # Clear state
    await state.clear()
    await callback.answer()

# Cancel account addition
@router.callback_query(F.data == "cancel_add_account")
async def cancel_add_account(callback: types.CallbackQuery, state: FSMContext):
    """Cancel account addition process"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Добавление аккаунта отменено.",
        reply_markup=get_back_to_accounts_keyboard()
    )
    await callback.answer()

# Check account health
@router.callback_query(F.data.startswith("check_account:"))
async def check_account_health(callback: types.CallbackQuery):
    """Check account health and status"""
    account_id = int(callback.data.split(":")[1])
    
    try:
        # Show loading message
        await callback.message.edit_text(
            "⏳ Проверка состояния аккаунта...",
            reply_markup=None
        )
        
        # Call API to check account health
        response = await api_client.post(f"/api/accounts/{account_id}/check")
        health_data = response.json()
        
        # Format status message
        status_emoji = {
            "active": "✅",
            "cooling_down": "⏳",
            "banned": "🚫",
            "needs_verification": "⚠️",
            "limited": "⚠️",
            "inactive": "❌"
        }.get(health_data["status"], "❓")
        
        status_text = (
            f"📱 {hbold('Статус аккаунта:')}\n\n"
            f"Статус: {status_emoji} {health_data['status'].upper()}\n"
            f"Подключение: {'✅ Успешно' if health_data['is_connected'] else '❌ Ошибка'}\n"
            f"Авторизация: {'✅ Успешно' if health_data['is_authorized'] else '❌ Ошибка'}\n"
            f"Ограничения: {'⚠️ Обнаружены' if health_data['has_restrictions'] else '✅ Нет'}\n"
        )
        
        if health_data["details"]:
            status_text += f"\nℹ️ {hbold('Подробности:')} {health_data['details']}"
        
        await callback.message.edit_text(
            status_text,
            reply_markup=get_account_detail_keyboard(account_id)
        )
    except Exception as e:
        logger.error(f"Error checking account health: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при проверке состояния аккаунта.",
            reply_markup=get_account_detail_keyboard(account_id)
        )
    
    await callback.answer()

# Reset account limits
@router.callback_query(F.data.startswith("reset_account:"))
async def reset_account_limits(callback: types.CallbackQuery):
    """Reset account usage limits"""
    account_id = int(callback.data.split(":")[1])
    
    try:
        # Call API to reset account limits
        response = await api_client.post(f"/api/accounts/{account_id}/reset")
        
        if response.status_code == 200:
            await callback.message.edit_text(
                "✅ Лимиты аккаунта успешно сброшены.",
                reply_markup=get_account_detail_keyboard(account_id)
            )
        else:
            error_data = response.json()
            await callback.message.edit_text(
                f"❌ Ошибка при сбросе лимитов: {error_data.get('detail', 'Неизвестная ошибка')}",
                reply_markup=get_account_detail_keyboard(account_id)
            )
    except Exception as e:
        logger.error(f"Error resetting account limits: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при сбросе лимитов аккаунта.",
            reply_markup=get_account_detail_keyboard(account_id)
        )
    
    await callback.answer()

# Delete account handler
@router.callback_query(F.data.startswith("delete_account:"))
async def delete_account_callback(callback: types.CallbackQuery):
    """Handle account deletion"""
    account_id = int(callback.data.split(":")[1])
    
    # Create confirmation keyboard
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Подтвердить удаление", callback_data=f"confirm_delete_account:{account_id}"),
            types.InlineKeyboardButton(text="❌ Отменить", callback_data=f"account_details:{account_id}")
        ]
    ])
    
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить этот аккаунт? Это действие невозможно отменить.",
        reply_markup=keyboard
    )
    await callback.answer()

# Confirm delete account
@router.callback_query(F.data.startswith("confirm_delete_account:"))
async def confirm_delete_account(callback: types.CallbackQuery):
    """Confirm and process account deletion"""
    account_id = int(callback.data.split(":")[1])
    
    try:
        # Call API to delete account
        response = await api_client.delete(f"/api/accounts/{account_id}")
        
        if response.status_code == 204:
            await callback.message.edit_text(
                "✅ Аккаунт успешно удален.",
                reply_markup=get_back_to_accounts_keyboard()
            )
        else:
            error_data = response.json()
            await callback.message.edit_text(
                f"❌ Ошибка при удалении аккаунта: {error_data.get('detail', 'Неизвестная ошибка')}",
                reply_markup=get_account_detail_keyboard(account_id)
            )
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении аккаунта.",
            reply_markup=get_account_detail_keyboard(account_id)
        )
    
    await callback.answer()

# Back to accounts menu
@router.callback_query(F.data == "back_to_accounts")
async def back_to_accounts(callback: types.CallbackQuery):
    """Return to accounts menu"""
    await show_accounts_menu(callback.message)
    await callback.answer()