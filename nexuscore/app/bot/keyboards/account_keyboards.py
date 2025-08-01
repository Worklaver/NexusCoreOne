from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_accounts_menu_keyboard(accounts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Create keyboard for accounts menu with list of accounts
    
    Args:
        accounts: List of account objects from API
        
    Returns:
        InlineKeyboardMarkup: Keyboard with account buttons
    """
    keyboard = []
    
    # Add account buttons
    for account in accounts:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{account['phone']} ({account['status']})", 
                callback_data=f"account_details:{account['id']}"
            )
        ])
    
    # Add control buttons
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_account")
    ])
    
    keyboard.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_account_detail_keyboard(account_id: int) -> InlineKeyboardMarkup:
    """
    Create keyboard for account details
    
    Args:
        account_id: Account ID
        
    Returns:
        InlineKeyboardMarkup: Keyboard with account actions
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"check_account:{account_id}"),
            InlineKeyboardButton(text="🔄 Сбросить лимиты", callback_data=f"reset_account:{account_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Удалить аккаунт", callback_data=f"delete_account:{account_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к аккаунтам", callback_data="back_to_accounts")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_add_account_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with cancel button for account addition process
    
    Returns:
        InlineKeyboardMarkup: Keyboard with cancel button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_add_account")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_accounts_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with back button to accounts menu
    
    Returns:
        InlineKeyboardMarkup: Keyboard with back button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🔙 Назад к аккаунтам", callback_data="back_to_accounts")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)