from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

def get_parse_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for parse menu with main options
    
    Returns:
        InlineKeyboardMarkup: Keyboard with parse menu buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🆕 Новый парсинг", callback_data="start_new_parsing")
        ],
        [
            InlineKeyboardButton(text="📊 Активные задачи", callback_data="view_active_tasks")
        ],
        [
            InlineKeyboardButton(text="🗄️ Мои базы данных", callback_data="my_databases")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_parse_type_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for selecting parsing type
    
    Returns:
        InlineKeyboardMarkup: Keyboard with parse types
    """
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Участники", callback_data="parse_type:members")
        ],
        [
            InlineKeyboardButton(text="✍️ Авторы", callback_data="parse_type:writers")
        ],
        [
            InlineKeyboardButton(text="💬 Комментаторы", callback_data="parse_type:commenters")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="open_parse_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_parse_target_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for parse target input
    
    Returns:
        InlineKeyboardMarkup: Keyboard with cancel button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_parsing")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_parse_options_keyboard(parse_type: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Create keyboard for parsing options
    
    Args:
        parse_type: Type of parsing
    
    Returns:
        InlineKeyboardMarkup: Keyboard with options
    """
    keyboard = [
        [
            InlineKeyboardButton(text="100", callback_data="parse_limit:100")
        ],
        [
            InlineKeyboardButton(text="500", callback_data="parse_limit:500")
        ],
        [
            InlineKeyboardButton(text="1000", callback_data="parse_limit:1000")
        ],
        [
            InlineKeyboardButton(text="5000", callback_data="parse_limit:5000")
        ],
        [
            InlineKeyboardButton(text="Все (макс. 10000)", callback_data="parse_limit:0")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_parsing")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_parse_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard with back button to parse menu
    
    Returns:
        InlineKeyboardMarkup: Keyboard with back button
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🔙 Назад к парсингу", callback_data="open_parse_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)