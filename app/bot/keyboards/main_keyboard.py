from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for the main menu with all main functions
    
    Returns:
        InlineKeyboardMarkup: Keyboard with main menu buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(text="👤 Аккаунты", callback_data="open_accounts_menu")
        ],
        [
            InlineKeyboardButton(text="🔍 Парсинг", callback_data="open_parse_menu")
        ],
        [
            InlineKeyboardButton(text="➕ Инвайтинг", callback_data="open_invite_menu")
        ],
        [
            InlineKeyboardButton(text="❤️ Лайкинг комментариев", callback_data="open_like_menu")
        ],
        [
            InlineKeyboardButton(text="📊 Активные задачи", callback_data="open_tasks_menu")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="open_settings_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)