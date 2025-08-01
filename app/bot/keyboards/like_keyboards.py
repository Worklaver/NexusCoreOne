from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_like_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for like menu with main options
    
    Returns:
        InlineKeyboardMarkup: Keyboard with like menu buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🆕 Новый лайкинг", callback_data="start_new_like")
        ],
        [
            InlineKeyboardButton(text="📊 Активные задачи", callback_data="view_active_likes")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_like_target_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for like target input
    
    Returns:
        InlineKeyboardMarkup: Keyboard with cancel button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_like")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_like_options_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for like options
    
    Returns:
        InlineKeyboardMarkup: Keyboard with options
    """
    keyboard = [
        [
            InlineKeyboardButton(text="Стандартные (5-15с, 100 на аккаунт)", callback_data="like_options:5,15,100")
        ],
        [
            InlineKeyboardButton(text="Безопасные (15-30с, 50 на аккаунт)", callback_data="like_options:15,30,50")
        ],
        [
            InlineKeyboardButton(text="Агрессивные (2-5с, 200 на аккаунт)", callback_data="like_options:2,5,200")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_like")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_like_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with back button to like menu
    
    Returns:
        InlineKeyboardMarkup: Keyboard with back button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🔙 Назад к лайкингу", callback_data="open_like_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)