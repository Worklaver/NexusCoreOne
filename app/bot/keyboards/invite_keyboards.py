from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_invite_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for invite menu with main options
    
    Returns:
        InlineKeyboardMarkup: Keyboard with invite menu buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🆕 Новый инвайтинг", callback_data="start_new_invite")
        ],
        [
            InlineKeyboardButton(text="📊 Активные инвайты", callback_data="view_active_invites")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_invite_source_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for selecting invite source
    
    Returns:
        InlineKeyboardMarkup: Keyboard with source options
    """
    keyboard = [
        [
            InlineKeyboardButton(text="📊 Из базы данных", callback_data="invite_source:database")
        ],
        [
            InlineKeyboardButton(text="📝 Внешний список", callback_data="invite_source:external")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="open_invite_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_invite_target_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for invite target input
    
    Returns:
        InlineKeyboardMarkup: Keyboard with cancel button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_invite")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_invite_options_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for invite options
    
    Returns:
        InlineKeyboardMarkup: Keyboard with options
    """
    keyboard = [
        [
            InlineKeyboardButton(text="Стандартные (30-60с, 50 на аккаунт)", callback_data="invite_options:30,60,50")
        ],
        [
            InlineKeyboardButton(text="Безопасные (60-120с, 30 на аккаунт)", callback_data="invite_options:60,120,30")
        ],
        [
            InlineKeyboardButton(text="Агрессивные (15-30с, 100 на аккаунт)", callback_data="invite_options:15,30,100")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_invite")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_invite_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with back button to invite menu
    
    Returns:
        InlineKeyboardMarkup: Keyboard with back button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🔙 Назад к инвайтингу", callback_data="open_invite_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)