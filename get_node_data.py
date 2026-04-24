"""
get_node_data.py
Парсит поля select со страницы редактирования лота FunPay для конкретной ноды.

Требуются переменные окружения (или .env файл):
    FUNPAY_GOLDEN_KEY  — кука golden_key из браузера
    FUNPAY_PHPSESSID   — кука PHPSESSID из браузера
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv не обязателен, можно задавать переменные вручную

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

BASE_URL = "https://funpay.com"
SNODS_DIR = Path(os.getenv("SNODS_DIR", "snods"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    """Возвращает значение переменной окружения или бросает понятную ошибку."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Переменная окружения '{name}' не задана. "
            f"Добавьте её в .env файл или экспортируйте в терминале."
        )
    return value


def build_session() -> requests.Session:
    """Создаёт сессию с куками авторизации FunPay."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.cookies.update({
        "golden_key": _require_env("FUNPAY_GOLDEN_KEY"),
        "PHPSESSID":  _require_env("FUNPAY_PHPSESSID"),
        "locale":     "ru",
    })
    return session


def parse_selects(html: str) -> Dict[str, Dict[str, str]]:
    """
    Извлекает все <select> с их <option> из HTML страницы.

    Возвращает словарь вида:
        { "имя_поля": { "Текст опции": "значение", ... }, ... }
    """
    soup = BeautifulSoup(html, "html.parser")
    result: Dict[str, Dict[str, str]] = {}

    for select in soup.find_all("select"):
        name = select.get("name")
        if not name:
            continue

        options: Dict[str, str] = {}
        for option in select.find_all("option"):
            value = option.get("value", "")
            text = option.get_text(strip=True)
            if text:
                options[text] = value

        if options:
            result[name] = options

    return result


# ---------------------------------------------------------------------------
# Основной API
# ---------------------------------------------------------------------------

def get_node_fields(
    node_id: str | int,
    session: Optional[requests.Session] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Загружает страницу редактирования лота для ноды и возвращает её поля.

    Args:
        node_id: ID ноды FunPay.
        session: Готовая сессия requests. Если не передана — создаётся новая.

    Returns:
        Словарь { имя_поля: { текст_опции: значение } }.
    """
    node_id = str(node_id)
    own_session = session is None
    if own_session:
        session = build_session()

    try:
        url = f"{BASE_URL}/lots/offerEdit?node={node_id}"
        print(f"  Парсим ноду {node_id}: {url}")
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return parse_selects(response.text)
    finally:
        if own_session:
            session.close()


def create_node(node_id: str | int) -> None:
    """
    Парсит поля ноды и сохраняет их в snods/node_{node_id}.json.

    Args:
        node_id: ID ноды FunPay.
    """
    node_id = str(node_id)
    SNODS_DIR.mkdir(parents=True, exist_ok=True)

    result = get_node_fields(node_id)

    path = SNODS_DIR / f"node_{node_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"  Сохранено: {path} ({len(result)} полей)")
