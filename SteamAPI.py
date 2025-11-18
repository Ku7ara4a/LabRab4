import requests
import json

from logger import logger


# Класс для работы с Steam API
class SteamAPI:
    def __init__(self):
        self.base_url = "https://store.steampowered.com/api"
        self.game_aliases = {
            'ведьмак': 'The Witcher',
            'витчер': 'The Witcher',
            'киберпанк': 'Cyberpunk',
            'сайберпанк': 'Cyberpunk',
            'гта': 'Grand Theft Auto',
            'гта 5': 'Grand Theft Auto V',
            'гта5': 'Grand Theft Auto V',
            'контр страйк': 'Counter-Strike',
            'контр-страйк': 'Counter-Strike',
            'кс': 'Counter-Strike',
            'кс2': 'Counter-Strike 2',
            'дота': 'Dota',
            'дота 2': 'Dota 2',
            'скайрим': 'Skyrim',
            'фоллаут': 'Fallout',
            'ассасин': 'Assassin',
            'бэтмен': 'Batman',
            'резедент вил': 'Resident Evil',
            'арк': 'ARK',

            # Сокращения
            'cs': 'Counter-Strike',
            'cs2': 'Counter-Strike 2',
            'cs:go': 'Counter-Strike Global Offensive',
            'tf2': 'Team Fortress 2',
            'pubg': 'PLAYERUNKNOWN',
            'rdr2': 'Red Dead Redemption 2',
            'rdr 2': 'Red Dead Redemption 2',
            'ac': 'Assassin',
        }

        # Настройки регионов
        self.region_settings = {
            'RU': {'cc': 'ru', 'l': 'russian', 'currency': 'RUB'},
            'US': {'cc': 'us', 'l': 'russian', 'currency': 'USD'},
            'EU': {'cc': 'de', 'l': 'russian', 'currency': 'EUR'},
            'KZ': {'cc': 'kz', 'l': 'russian', 'currency': 'KZT'},
            'TR': {'cc': 'tr', 'l': 'russian', 'currency': 'TRY'},
            'AR': {'cc': 'ar', 'l': 'russian', 'currency': 'ARS'},
            'BR': {'cc': 'br', 'l': 'russian', 'currency': 'BRL'}
        }

    def get_region_params(self, region_code):
        """Получает параметры для региона"""
        return self.region_settings.get(region_code, self.region_settings['RU'])

    def search_game(self, game_name, region_code='RU'):
        """Обычный поиск игры в Steam с учетом региона"""
        try:
            url = f"{self.base_url}/storesearch"
            region_params = self.get_region_params(region_code)

            params = {
                'term': game_name,
                'l': region_params['l'],
                'cc': region_params['cc'],
                'limit': 5
            }

            logger.info(f'Поиск игры: {game_name} в регионе {region_code}')

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('items'):
                return data['items']
            return None

        except Exception as e:
            logger.error(f"Steam search error in region {region_code}: {e}")
            return None

    def smart_game_search(self, game_name, region_code='RU'):
        """Умный поиск игры с обработкой альтернативных названий и учетом региона"""
        # Сначала пробуем прямой поиск
        games = self.search_game(game_name, region_code)

        if games:
            return games

        # Если не найдено - пробуем варианты
        alternative_names = self.get_alternative_names(game_name)

        for alt_name in alternative_names:
            games = self.search_game(alt_name, region_code)
            if games:
                return games

        return None

    def get_alternative_names(self, game_name):
        """Генерирует альтернативные названия для поиска"""
        game_name_lower = game_name.lower()
        alternatives = []

        # Проверяем прямые совпадения в словаре псевдонимов
        for alias, official_name in self.game_aliases.items():
            if alias in game_name_lower:
                alternatives.append(official_name)

        # Добавляем оригинальное название на случай опечаток
        alternatives.append(game_name)

        return alternatives

    def get_search_suggestions(self, game_name):
        """Возвращает умные подсказки для поиска"""
        game_name_lower = game_name.lower()

        suggestions_map = {
            'ведьмак': "💡 Попробуйте: `The Witcher 3`",
            'витчер': "💡 Попробуйте: `The Witcher`",
            'киберпанк': "💡 Попробуйте: `Cyberpunk 2077`",
            'сайберпанк': "💡 Попробуйте: `Cyberpunk 2077`",
            'гта': "💡 Попробуйте: `GTA V` или `Grand Theft Auto`",
            'контр страйк': "💡 Попробуйте: `Counter-Strike 2`",
            'кс': "💡 Попробуйте: `Counter-Strike 2` или `CS2`",
            'дота': "💡 Попробуйте: `Dota 2`",
            'майнкрафт': "💡 Попробуйте: `Minecraft`",
            'скайрим': "💡 Попробуйте: `Skyrim`",
            'фоллаут': "💡 Попробуйте: `Fallout 4`",
        }

        for keyword, suggestion in suggestions_map.items():
            if keyword in game_name_lower:
                return suggestion

        # Общие советы
        return "💡 *Советы:*\n• Используйте английское название\n• Проверьте правильность написания\n• Попробуйте сокращенное название"

    def get_region_issue_message(self, region_code):
        """Возвращает сообщение о возможных проблемах с регионом"""
        region_messages = {
            'RU': "⚠️ В России могут быть ограничения на некоторые игры",
            'TR': "⚠️ В Турции могут быть региональные ограничения",
            'AR': "⚠️ В Аргентине могут быть региональные ограничения",
        }

        return region_messages.get(region_code,
                                   "⚠️ В вашем регионе могут быть ограничения на некоторые игры")

    def get_game_details(self, game_id, region_code='RU'):
        """Получение детальной информации об игре с учетом региона"""
        try:
            url = f"{self.base_url}/appdetails"
            region_params = self.get_region_params(region_code)

            params = {
                'appids': game_id,
                'l': region_params['l'],
                'cc': region_params['cc'],
                'currency': region_params['currency']
            }

            logger.info(f'Запрос подробностей об {game_id} для региона {region_code}')

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if str(game_id) in data and data[str(game_id)].get('success'):
                game_data = data[str(game_id)]['data']
                # Добавляем ID игры в данные для удобства
                game_data['id'] = game_id
                return game_data
            else:
                logger.warning(f"Игра {game_id} не найдена или недоступна в регионе {region_code}")
                return None

        except Exception as e:
            logger.error(f"Steam details error for {game_id} in region {region_code}: {e}")
            return None

    def format_game_info(self, game_data, region_code='RU'):
        """Форматирование информации об игре для Telegram с учетом региона"""
        try:
            # Основная информация
            name = game_data.get('name', 'Неизвестно')
            price_info = game_data.get('price_overview', {})

            logger.info(f"Формирование информации об: {name} для региона {region_code}")

            # Обработка цены
            if price_info:
                price = f"💰 {price_info.get('final_formatted', 'Бесплатно')}"
                if price_info.get('discount_percent', 0) > 0:
                    price += f" (скидка {price_info['discount_percent']}% 🔥)"
            else:
                price = "🤑 Бесплатно 🤑"

            # Дата выхода
            release_date = game_data.get('release_date', {})
            if release_date.get('coming_soon'):
                release_info = "🕐 Скоро выйдет"
            else:
                release_info = f"📅 {release_date.get('date', 'Неизвестно')}"

            # Разработчики и издатели
            developers = ", ".join(game_data.get('developers', [])) or "Неизвестно"
            publishers = ", ".join(game_data.get('publishers', [])) or "Неизвестно"

            # Жанры
            genres = [genre['description'] for genre in game_data.get('genres', [])]
            genres_str = ", ".join(genres) if genres else "Не указаны"

            # Рейтинги
            metacritic = game_data.get('metacritic', {})
            metacritic_score = f"⭐️ {metacritic.get('score', 'N/A')}" if metacritic else "Оценка не указана"

            # Описание (обрезаем если слишком длинное)
            description = game_data.get('short_description', 'Описание отсутствует')
            if len(description) > 400:
                description = description[:400] + "..."

            # Информация о регионе
            region_info = f"🌍 Регион: {region_code}"

            # Формируем сообщение
            message = f"""
🎮 *{name}*

{price}
{release_info}
{metacritic_score}
{region_info}

*Разработчик:* {developers}
*Издатель:* {publishers}
*Жанры:* {genres_str}

📖 *Описание:*
{description}

[Открыть в Steam](https://store.steampowered.com/app/{game_data.get('steam_appid', '')})
            """

            return message.strip()

        except Exception as e:
            logger.error(f"Format error: {e}")
            return f"❌ Ошибка при форматировании информации об игре"