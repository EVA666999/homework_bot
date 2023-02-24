import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
import telegram.ext
from dotenv import load_dotenv

from errors import connectionerror, exception, typerror

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RETRY_PERIOD = os.getenv("RETRY_TIME", 600)
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
PAYLOAD = {"from_date": int(time.time())}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


class ConnectionError(Exception):
    """Кастомное исключение ConnectionError."""

    pass


def check_tokens():
    """Проверяет, заданы ли все необходимые токены."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Проверяет отправкау сообщения в Telegram чат."""
    try:
        logging.debug(f"Начало отправки сообщения в чат {TELEGRAM_CHAT_ID}.")
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(
            f"Отправка сообщения в чат {TELEGRAM_CHAT_ID} выполнена успешно."
            "Текст сообщения: {message}"
        )
    except telegram.error.TelegramError:
        logging.error(
            f"Ошибка отправки сообщения в чат {TELEGRAM_CHAT_ID}."
            "Параметры: bot={bot}, text={message}, chat_id={TELEGRAM_CHAT_ID}"
        )
        raise TypeError


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API."""
    try:
        logging.debug(f"Отправка запроса к API с параметрами: {timestamp}")
        timestamp = PAYLOAD
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError(f"Код ответа API: {response.status_code}")
    except ConnectionError:
        send_message(
            TELEGRAM_CHAT_ID,
            message=logging.error(f"Код ответа API: {response.status_code}"),
        )
    except requests.RequestException:
        return False
    return response.json()


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    logging.debug(f"Начало провери ответа {response}")
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
             "Ожидается список.")
        )
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    logging.debug("Начало проверки статуса")
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
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s, %(levelname)s, %(message)s, %(name)s, "
        "%(filename)s, %(funcName)s, %(lineno)s'"
    )
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
    if not get_api_answer(timestamp=PAYLOAD):
        logging.error(
            (
                f"Недоступность эндпоинта {ENDPOINT} недоступен. "
                f"Код ответа API: {HTTPStatus}"
            )
        )
    if not check_tokens():
        logging.critical("Неправильный токен.")
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        bot.stop()
        sys.exit(message=("Неправильный токен."))
    timestamp = int(time.time())
    start_message = ""
    while True:
        try:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != start_message:
                    start_message = message
                    send_message(bot, message)
        except ConnectionError as error:
            connectionerror(error)
        except TypeError as error:
            typerror(error)
        except Exception as error:
            exception(error)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
