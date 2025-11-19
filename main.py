import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import StateFilter
import json
import os

from DataSetAnalys import (create_genre_analysis,
                           load_data_set,
                           create_top_games_plot,
                           get_basic_stats,
                           create_playtime_distribution,
                           test_playtime_achievements_correlation,
                           test_playtime_is_assymetryc)
from logger import logger
from SteamAPI import SteamAPI

# Token.txt - файл с одним токеном, добавлен в gitignore
with open('Token.txt', 'r') as f:
    TOKEN = f.read()

bot = telebot.TeleBot(TOKEN)
steam_api = SteamAPI()

# Файл для хранения данных пользователей
USERS_FILE = 'users.json'

df = load_data_set()
stats = get_basic_stats(df)

# Загрузка пользователей из JSON
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}
    return {}


# Сохранение пользователей в JSON
def save_users():
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_regions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving users: {e}")


# Хранилище регионов пользователей
user_regions = load_users()


def get_user_region(user_id, username):
    """Получает регион пользователя (по умолчанию Россия)"""
    if str(user_id) not in user_regions:
        # Создаем запись для нового пользователя
        user_regions[str(user_id)] = {
            'username': username,
            'region': 'RU'
        }
        save_users()
    # Обновляем username, если он изменился
    elif user_regions[str(user_id)]['username'] != username:
        user_regions[str(user_id)]['username'] = username
        save_users()
    return user_regions[str(user_id)]['region']


def set_user_region(user_id, username, region_code):
    """Устанавливает регион пользователя и сохраняет в JSON"""
    user_regions[str(user_id)] = {
        'username': username,
        'region': region_code
    }
    save_users()

# Определяем состояния
class GameStates(StatesGroup):
    waiting_for_game_name = State()
    waiting_for_region = State()


# Регистрируем фильтр состояний
bot.add_custom_filter(StateFilter(bot))


def get_region_keyboard():
    """Клавиатура для выбора региона"""
    markup = types.InlineKeyboardMarkup(row_width=2)

    regions = [
        ("Россия", "RU"),
        ("США", "US"),
        ("Европа", "EU"),
        ("Казахстан", "KZ"),
        ("Турция", "TR"),
        ("Аргентина", "AR"),
        ("Бразилия", "BR")
    ]

    buttons = []
    for region_name, region_code in regions:
        buttons.append(types.InlineKeyboardButton(region_name, callback_data=f"set_region:{region_code}"))

    # Распределяем кнопки по 2 в ряд
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(buttons[i], buttons[i + 1])
        else:
            markup.add(buttons[i])

    return markup


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    logger.info(f"Пользователь {user.username} (ID: {user.id}) запустил бота")

    # Получаем или создаем запись пользователя
    user_region = get_user_region(user.id, user.username)

    welcome_message = f"""
    Привет, {user.first_name}! Я GameChecker!
    Я помогу тебе узнать о компьютерных играх.

    📍 *Текущий регион: {user_region}*

    Выберите ваш регион для начала работы:
    """

    bot.send_message(
        message.chat.id,
        welcome_message,
        parse_mode='Markdown',
        reply_markup=get_region_keyboard()
    )


@bot.message_handler(commands=['region'])
def change_region(message):
    """Смена региона"""
    user = message.from_user
    current_region = get_user_region(user.id, user.username)

    warning_text = f"""
⚠️ *Внимание! Выбор региона влияет на:*
• Доступность игр в вашем регионе
• Цены и валюту отображения
• Результаты поиска

*Текущий регион: {current_region}*

Выберите новый регион:
    """

    bot.send_message(
        message.chat.id,
        warning_text,
        parse_mode='Markdown',
        reply_markup=get_region_keyboard()
    )


@bot.message_handler(commands=['help'])
def send_help(message):
    user = message.from_user
    current_region = get_user_region(user.id, user.username)

    logger.info(f"Пользователь {user.username} запросил помощь")

    help_message = f"""
📋 *Список доступных команд:*

/start - начало работы с ботом
/search - найти игру по названию 🔍
/region - сменить регион (текущий: {current_region}) 🌍
/help - получить список доступных команд

*Информация о пользователе:*
👤 Username: @{user.username}
🌍 Регион: {current_region}
🆔 ID: {user.id}
    """
    bot.reply_to(message, help_message, parse_mode='Markdown')


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
    user = message.from_user
    user_region = get_user_region(user.id, user.username)

    search_text = f"""
🔍 *Поиск игр* (Регион: {user_region})

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

    bot.set_state(user.id, GameStates.waiting_for_game_name, message.chat.id)
    logger.info(f"Пользователь {user.username} начал поиск в регионе {user_region}")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Отменить поиск", callback_data="cancel_search"))

    bot.send_message(message.chat.id, search_text,
                     reply_markup=markup, parse_mode='Markdown')


@bot.message_handler(state=GameStates.waiting_for_game_name)
def handle_game_name_advanced(message):
    """Продвинутый поиск с обработкой альтернативных названий"""
    try:
        game_name = message.text.strip()
        user = message.from_user
        user_region = get_user_region(user.id, user.username)

        if len(game_name) < 2:
            send_search_prompt(message.chat.id, "❌ Минимум 2 символа. Попробуйте еще раз:")
            return

        search_msg = bot.send_message(message.chat.id, f"🔍 Ищу *{game_name}* в регионе {user_region}...",
                                      parse_mode='Markdown')

        # Умный поиск с учетом региона
        games = steam_api.smart_game_search(game_name, user_region)

        if not games:
            # Если поиск не удался, проверяем возможную причину региона
            region_issue_msg = steam_api.get_region_issue_message(user_region)

            bot.delete_message(message.chat.id, search_msg.message_id)

            suggestion_text = f"""
❌ *{game_name}* не найдена в регионе {user_region}.

{region_issue_msg}

*Попробуйте:*
• Ввести другое название
• Сменить регион командой /region
• Использовать английское название
            """
            send_search_prompt(message.chat.id, suggestion_text)
            return

        # Если найдено несколько вариантов - показываем выбор
        if len(games) > 1:
            show_game_options(message.chat.id, games, search_msg.message_id, user_region)
            return

        # Один результат - показываем сразу
        bot.delete_state(user.id, message.chat.id)
        process_found_game(games[0], message.chat.id, search_msg.message_id, user_region)

    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        send_search_prompt(message.chat.id, "❌ Ошибка поиска. Попробуйте еще раз:")


def show_game_options(chat_id, games, search_msg_id, user_region):
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
            callback_data=f"select_game:{game['id']}:{user_region}"
        ))

    markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_search"))

    bot.edit_message_text(
        f"🎯 *Найдено несколько игр в регионе {user_region}:*\n"
        "(Если игры нет в списке попробуйте написать название на английском)\n"
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
        parts = call.data.split(':')
        game_id = int(parts[1])
        user_region = parts[2] if len(parts) > 2 else "RU"

        bot.delete_state(call.from_user.id, call.message.chat.id)

        # Показываем загрузку
        bot.edit_message_text(
            "🔄 Загружаем информацию...",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        # Получаем детали игры с учетом региона
        game_details = steam_api.get_game_details(game_id, user_region)

        if game_details:
            game_info = steam_api.format_game_info(game_details, user_region)
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
            region_issue_msg = steam_api.get_region_issue_message(user_region)
            error_text = f"❌ Ошибка загрузки информации об игре\n\n{region_issue_msg}"
            bot.edit_message_text(
                error_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )

    except Exception as e:
        logger.error(f"Game selection error: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки")


def process_found_game(game_data, chat_id, search_msg_id, user_region):
    """Обрабатывает найденную игру"""
    game_id = game_data['id']
    game_details = steam_api.get_game_details(game_id, user_region)

    if not game_details:
        # Ошибка загрузки - возвращаем в состояние поиска
        bot.set_state(chat_id, GameStates.waiting_for_game_name, chat_id)
        region_issue_msg = steam_api.get_region_issue_message(user_region)

        error_text = f"""
❌ Не удалось загрузить информацию об игре *{game_data['name']}* в регионе {user_region}

{region_issue_msg}

Попробуйте другое название или смените регион:
        """

        send_search_prompt(chat_id, error_text)
        bot.delete_message(chat_id, search_msg_id)
        return

    # Успешный поиск - показываем результат
    game_info = steam_api.format_game_info(game_details, user_region)
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


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_region:'))
def handle_set_region(call):
    """Обработчик установки региона"""
    region_code = call.data.split(':')[1]
    user = call.from_user

    # Сохраняем регион пользователя
    set_user_region(user.id, user.username, region_code)

    region_names = {
        'RU': 'Россия',
        'US': 'США',
        'EU': 'Европа',
        'KZ': 'Казахстан',
        'TR': 'Турция',
        'AR': 'Аргентина',
        'BR': 'Бразилия'
    }

    region_name = region_names.get(region_code, region_code)

    success_text = f"""
✅ Регион успешно изменен на *{region_name}*

⚠️ *Влияние на поиск:*
• Цены будут отображаться в местной валюте
• Некоторые игры могут быть недоступны в вашем регионе
• Результаты поиска зависят от региональных ограничений

Используйте /search для поиска игр
    """

    bot.edit_message_text(
        success_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode='Markdown'
    )

    logger.info(f"Пользователь {user.username} установил регион {region_code}")


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

@bot.message_handler(commands=['top_games'])
def send_top_games(message):
    try:
        bot.send_message(message.chat.id, "Создаю График...")
        plot_buffer = create_top_games_plot(df)
        logger.info(f"Пользователь {message.from_user.username} запросил топ игр среди друзей")
        bot.send_photo(message.chat.id, plot_buffer, caption=f"Всего игр : {stats['total_games']}"
                                                             f" Игроков : {stats['total_players']}")
    except Exception as e:
        logger.error(f"Ошибка отправления графика: {e}")
        bot.send_message(message.chat.id, f"Ошибка при создании графика: {e}")

@bot.message_handler(commands=['playtime'])
def senf_playtime_stats(message):
    try:
        bot.send_message(message.chat.id, "Анализирую время игры...")
        plot_buffer = create_playtime_distribution(df)
        logger.info(f"Пользователь {message.from_user.username} запросил время игры")
        caption = f'Макс: {stats['max_playtime']:.0f}ч, Среднее: {stats['avg_playtime']:.0f}ч'
        bot.send_photo(message.chat.id, plot_buffer, caption=caption)
    except Exception as e:
        logger.error(f"Ошибка отправления графика {e}")
        bot.send_message(message.chat.id, f"Ошибка при создании графика: {e}")


@bot.message_handler(commands=['genres'])
def send_genre_stats(message):
    try:
        bot.send_message(message.chat.id, "Анализирую жанры...")
        plot_buffer = create_genre_analysis(df)
        logger.info(f"Пользователь {message.from_user.username} запросил жанры")
        caption = f"Всего жанров: {stats['total_genres']}"
        bot.send_photo(message.chat.id, plot_buffer, caption=caption)

    except Exception as e:
        logger.error(f"Ошибка отправления графика {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands = ['correlation'])
def send_correlation_stats(message):
    try:
        correlation, strength, direction, group_stats = test_playtime_achievements_correlation(df)
        if strength == 'очень слабая' or strength == 'слабая':
            results = ('Скорее всего достижения не зависят от времени\n'
                       'Другие факторы влияют сильнее')
        else:
            results = 'Скорее всего достижения зависят от времени'

        logger.info(f"Пользователь {message.from_user.username} запросил корреляцию")
        bot.send_message(message.chat.id, f"Корреляция время-достижения: {correlation}\n"
                                          f"{strength} связь\n"
                                          f"{results}")
    except Exception as e:
        logger.error(f"Ошибка при построении корреляции {e}")
        bot.send_message(message.chat.id, f"Ошибка при построении корреляции: {e}")

@bot.message_handler(commands = ['asymmetryc'])
def send_asymmetryc_stats(message):
    try:
        assym = test_playtime_is_assymetryc(df)
        logger.info(f"Пользователь {message.from_user.username} запросил ассиметрию")
        if abs(assym) < 0.5:
            results = 'распределение близко к симметричному'
        elif 0.5 <= abs(assym) < 1:
            results = 'распределение умеренно ассиметричное'
        else:
            results = 'распределение ассиметричное'

        if assym > 0:
            direction = "правосторонняя (положительная)"
        elif assym < 0:
            direction = "левосторонняя (отрицательная)"
        else:
            direction = "симметричное"

        bot.send_message(message.chat.id, f"Ассиметрия времени игры: {assym}\n"
                                          f"Что значит, что {results}\n"
                                          f"Со стороной {direction}\n")
    except Exception as e:
        logger.error(f"Ошибка при ассиметрии {e}")
        bot.send_message(message.chat.id, f"Ошибка при запросе ассиметрии: {e}")

# Сохраняем пользователей при завершении работы
import atexit

atexit.register(save_users)

bot.polling(none_stop=True)