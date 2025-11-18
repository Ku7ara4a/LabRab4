import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import StateFilter


from logger import logger
from SteamAPI import SteamAPI

#Token.txt - файл с одним токеном, добавлен в gitignore
with open('Token.txt','r') as f:
    TOKEN = f.read()

bot = telebot.TeleBot(TOKEN)
steam_api = SteamAPI()


@bot.message_handler(commands=['start'])
def send_welcome(message):

    logger.info(f"Пользователь {message.from_user.username} запустил бота")

    welcome_message = """
    Привет! Я GameChecker!\nЯ помогу тебе узнать о компьютерных играх.
    """
    bot.reply_to(message, welcome_message)


@bot.message_handler(commands=['help'])
def send_help(message):

    user = message.from_user
    logger.info(f"Пользователь {user.first_name} запросил помощь")

    help_message = """
    Список доступных команд:
    /start - начало работы с ботом
    /search - найти игру по названию🔍
    /help - получить список доступных команд
    """
    bot.reply_to(message, help_message)

# Определяем состояния
class GameStates(StatesGroup):
    waiting_for_game_name = State()


# Регистрируем фильтр состояний
bot.add_custom_filter(StateFilter(bot))


def send_search_prompt(chat_id, text):
    """Отправляет сообщение с предложением ввести название и кнопкой отмены"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Отменить поиск", callback_data="cancel_search"))

    bot.send_message(
        chat_id,
        text,
        reply_markup=markup,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['search'])
def handle_search_ultimate(message):
    """Поиск с поддержкой альтернативных названий"""
    bot.set_state(message.from_user.id, GameStates.waiting_for_game_name, message.chat.id)

    user = message.from_user
    logger.info(f"Пользователь {user.first_name} начал поиск")

    search_text = """
🔍 *Умный поиск игр*

Введите название игры на *русском* или *английском*:

*Примеры русских названий:*
• Ведьмак 3
• Киберпанк 2077
• ГТА 5
• КС 2
• Дота 2

*Или английские названия:*
• The Witcher 3  
• Cyberpunk 2077
• GTA V
• Counter-Strike 2
• Dota 2

Бот сам подберет правильное название! 🎯
    """

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Отменить поиск", callback_data="cancel_search"))

    bot.send_message(message.chat.id, search_text,
                     reply_markup=markup, parse_mode='Markdown')


@bot.message_handler(state=GameStates.waiting_for_game_name)
def handle_game_name_advanced(message):
    """Продвинутый поиск с обработкой альтернативных названий"""
    try:
        game_name = message.text.strip()

        if len(game_name) < 2:
            send_search_prompt(message.chat.id, "❌ Минимум 2 символа. Попробуйте еще раз:")
            return

        search_msg = bot.send_message(message.chat.id, f"🔍 Ищу *{game_name}*...", parse_mode='Markdown')

        # Умный поиск
        games = steam_api.smart_game_search(game_name)

        if not games:
            #Если поиск не удался, предлагаем варианты
            suggestions = steam_api.get_search_suggestions(game_name)
            bot.delete_message(message.chat.id, search_msg.message_id)

            suggestion_text = f"""
❌ *{game_name}* не найдена.

{suggestions}

*Попробуйте ввести другое название:*
            """
            send_search_prompt(message.chat.id, suggestion_text)
            return

        # Если найдено несколько вариантов - показываем выбор
        if len(games) > 1:
            show_game_options(message.chat.id, games, search_msg.message_id)
            return

        # Один результат - показываем сразу
        bot.delete_state(message.from_user.id, message.chat.id)
        process_found_game(games[0], message.chat.id, search_msg.message_id)

    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        send_search_prompt(message.chat.id, "❌ Ошибка поиска. Попробуйте еще раз:")


def show_game_options(chat_id, games, search_msg_id):
    """Показывает варианты найденных игр для выбора"""
    markup = types.InlineKeyboardMarkup()

    for i, game in enumerate(games[:5]):  # Ограничиваем 5 вариантами
        game_name = game['name']
        # Обрезаем длинные названия
        if len(game_name) > 35:
            display_name = game_name[:32] + "..."
        else:
            display_name = game_name

        markup.add(types.InlineKeyboardButton(
            f"🎮 {display_name}",
            callback_data=f"select_game:{game['id']}"
        ))

    markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_search"))

    bot.edit_message_text(
        "🎯 *Найдено несколько игр:*\n "
        "(Если игры нет в списке попробуйте написать название на английском)\n "
        "Выберите нужную игру:",
        chat_id=chat_id,
        message_id=search_msg_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_game:'))
def handle_game_selection(call):
    """Обработчик выбора игры из списка"""
    try:
        game_id = int(call.data.split(':')[1])
        bot.delete_state(call.from_user.id, call.message.chat.id)

        # Показываем загрузку
        bot.edit_message_text(
            "🔄 Загружаем информацию...",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        # Получаем детали игры
        game_details = steam_api.get_game_details(game_id)

        if game_details:
            game_info = steam_api.format_game_info(game_details)
            header_image = game_details.get('header_image')

            if header_image:
                try:
                    bot.send_photo(call.message.chat.id, header_image, caption=game_info, parse_mode='Markdown')
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except:
                    bot.edit_message_text(game_info, chat_id=call.message.chat.id,
                                          message_id=call.message.message_id, parse_mode='Markdown')
            else:
                bot.edit_message_text(game_info, chat_id=call.message.chat.id,
                                      message_id=call.message.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(
                "❌ Ошибка загрузки информации об игре",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )

    except Exception as e:
        logger.error(f"Game selection error: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки")


def process_found_game(game_data, chat_id, search_msg_id):
    """Обрабатывает найденную игру"""
    game_id = game_data['id']
    game_details = steam_api.get_game_details(game_id)

    if not game_details:
        # Ошибка загрузки - возвращаем в состояние поиска
        bot.set_state(chat_id, GameStates.waiting_for_game_name, chat_id)
        send_search_prompt(
            chat_id,
            f"❌ Не удалось загрузить информацию об игре *{game_data['name']}*\n\nПопробуйте другое название:"
        )
        bot.delete_message(chat_id, search_msg_id)
        return

    # Успешный поиск - показываем результат
    game_info = steam_api.format_game_info(game_details)
    header_image = game_details.get('header_image')

    if header_image:
        try:
            bot.send_photo(chat_id, header_image, caption=game_info, parse_mode='Markdown')
            bot.delete_message(chat_id, search_msg_id)
        except:
            bot.edit_message_text(game_info, chat_id=chat_id,
                                  message_id=search_msg_id, parse_mode='Markdown')
    else:
        bot.edit_message_text(game_info, chat_id=chat_id,
                              message_id=search_msg_id, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data == "cancel_search")
def handle_cancel_search(call):
    """Обработчик нажатия на кнопку отмены"""
    try:
        bot.delete_state(call.from_user.id, call.message.chat.id)
        bot.edit_message_text(
            "❌ Поиск отменен",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.answer_callback_query(call.id, "Поиск отменен")
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        bot.answer_callback_query(call.id, "Ошибка отмены")


bot.polling(none_stop=True)