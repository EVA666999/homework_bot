import logging
from dotenv import load_dotenv
import os
import sys

load_dotenv()

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def connectionerror(error):
    """Сбой в работе программы."""
    message = f"Сбой в работе программы: {error}."
    logging.critical(message)


def typerror(error):
    """Сбой Ошибка типа данных."""
    message = f"Ошибка типа данных: {error},"
    logging.critical(message)


def exception(error):
    """Сбой Необработанное исключение."""
    message = f"Необработанное исключение: {error}."
    logging.critical(message)


def message_error(error):
    """Сбой Ошибка отправки сообщения в телеграм."""
    message = f"Ошибка отправки сообщения в телеграм: {error}."
    logging.critical(message)
    sys.exit(message=("Ошибка: создайте бота"))
