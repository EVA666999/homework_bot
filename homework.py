import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
import telegram.ext
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
PAYLOAD = {"from_date": int(time.time())}


logger = logging.getLogger(__name__)
# Устанавливаем уровень, с которого логи будут сохраняться в файл
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s, %(levelname)s, %(message)s")
handler = RotatingFileHandler(
    "my_logger.log",
    maxBytes=50000000,
    backupCount=5,
    encoding="utf-8",
)
handler.setFormatter(formatter)
logger.addHandler(
    handler,
)


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens():
    """Проверяет, заданы ли все необходимые токены."""
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    if not all(tokens):
        logger.critical(f"Неправильный токен {tokens}.")
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        bot.stop()


def send_message(bot, message):
    """Проверяет отправкау сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Сообщение отправлено успешно.")
    except Exception:
        logger.error("Ошибочка :(.")
        raise TypeError


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API."""
    try:
        timestamp = PAYLOAD
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if response.status_code == 200:
            return response.json()
        if response.status_code != 200:
            logger.error(
                (f"Недоступность эндпоинта {ENDPOINT} недоступен. "
                 f"Код ответа API: {response.status_code}")
            )
            send_message(
                TELEGRAM_CHAT_ID,
                message=logger.error(f"Код ответа API: {response.status_code}")
            )
    except requests.RequestException:
        return False
    return response.json()


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError("Неверный тип данных. Ожидается словарь.")
    if "homeworks" not in response or "current_date" not in response:
        raise TypeError(
            ("Ответ не соответствует документации. "
             "Отсутствуют необходимые ключи.")
        )
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        raise TypeError(
            ('Неверный тип данных для значения ключа "homeworks". '
             'Ожидается список.')
        )
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if "homework_name" not in homework:
        raise TypeError(
            f"Отсутствует ключ {homework_name} в ответе API домашней работы"
        )
    if homework_status is None:
        raise KeyError(
            f"Отсутствует ключ {homework_status} в ответе API домашней работы"
        )
    if verdict is None:
        raise KeyError(
            (f"Отсутствует статус {homework_status} в ответе "
             "API домашней работы")
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    start_message = ""
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != start_message:
                    start_message = message
                    send_message(bot, message)
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
