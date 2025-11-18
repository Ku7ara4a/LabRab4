import requests
import json

from logger import logger

# Класс для работы с Steam API
class SteamAPI:
    def __init__(self):
        self.base_url = "https://store.steampowered.com/api"
        self.game_aliases = {
            # Русские названия
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
            'майнкрафт': 'Minecraft',
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

    def search_game(self, game_name):
        """Обычный поиск игры в Steam"""
        try:
            url = f"{self.base_url}/storesearch"
            params = {
                'term': game_name,
                'l': 'russian',
                'cc': 'ru',
                'limit': 5
            }

            logger.info(f'Поиск игры: {game_name}')

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data['items']:
                return data['items']
            return None

        except Exception as e:
            logger.error(f"Steam search error: {e}")
            return None

    def smart_game_search(self, game_name):
        """Умный поиск игры с обработкой альтернативных названий"""
        # Сначала пробуем прямой поиск
        games = self.search_game(game_name)

        if games:
            return games

        # Если не найдено - пробуем варианты
        alternative_names = self.get_alternative_names(game_name)

        for alt_name in alternative_names:
            games = self.search_game(alt_name)
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

    def get_game_details(self, game_id):
        """Получение детальной информации об игре"""
        try:
            url = f"{self.base_url}/appdetails"
            params = {
                'appids': game_id,
                'l': 'russian',
                #ПРИМЕЧАНИЕ!!!
                #МОЖНО УКАЗАТЬ КОД СТРАНЫ НО ЕСЛИ ИГРЫ НЕТ В МАГАЗИНЕ СТРАНЫ СТИМА, ТО ОН НЕ СМОЖЕТ ЗАГРУЗИТЬ
            }

            logger.info(f'Запрос подробностей об {game_id}')

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if str(game_id) in data and data[str(game_id)]['success']:
                return data[str(game_id)]['data']
            return None

        except Exception as e:
            logger.error(f"Steam details error: {e}")
            return None

    def format_game_info(self, game_data):
        """Форматирование информации об игре для Telegram"""
        try:
            # Основная информация
            name = game_data.get('name', 'Неизвестно')
            price_info = game_data.get('price_overview', {})

            logger.info(f"Формирование информации об: {name}")

            # Обработка цены
            if price_info:
                price = f"Стоимость {price_info.get('final_formatted', 'Бесплатно')}"
                if price_info.get('discount_percent', 0) > 0:
                    price += f" (скидка {price_info['discount_percent']}% 🔥)"
            else:
                price = "🤑 Бесплатно 🤑"

            # Дата выхода
            release_date = game_data.get('release_date', {})
            if release_date.get('coming_soon'):
                release_info = "🕐 Скоро выйдет"
            else:
                release_info = f"Дата выхода: {release_date.get('date', 'Неизвестно')}"

            # Разработчики и издатели
            developers = ", ".join(game_data.get('developers', [])) or "Неизвестно"
            publishers = ", ".join(game_data.get('publishers', [])) or "Неизвестно"

            # Жанры
            genres = [genre['description'] for genre in game_data.get('genres', [])]
            genres_str = ", ".join(genres) if genres else "Не указаны"

            # Рейтинги
            metacritic = game_data.get('metacritic', {})
            metacritic_score = f"Оценка ⭐️ {metacritic.get('score', 'N/A')}" if metacritic else "Оценка метакритик не указана"

            # Описание (обрезаем если слишком длинное)
            description = game_data.get('short_description', 'Описание отсутствует')
            if len(description) > 400:
                description = description[:400] + "..."

            # Формируем сообщение
            message = f"""
🎮 *{name}*

{price}
{release_info}
{metacritic_score}

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
