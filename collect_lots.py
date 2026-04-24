"""
collect_lots.py
Собирает лоты с профилей FunPay и формирует JSON для дальнейшей обработки.

Требуются переменные окружения (или .env файл):
    FUNPAY_GOLDEN_KEY  — кука golden_key из браузера  (нужна только get_node_data)
    FUNPAY_PHPSESSID   — кука PHPSESSID из браузера   (нужна только get_node_data)

Опциональные переменные:
    SNODS_DIR          — папка для кэша нод (по умолчанию "snods")
    REQUEST_TIMEOUT    — таймаут запросов в секундах (по умолчанию 30)
    USER_AGENT         — User-Agent для запросов
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from get_node_data import create_node, get_node_fields, build_session

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Настройки — меняйте здесь или через переменные окружения / .env
# ---------------------------------------------------------------------------

# ID профилей FunPay, которые нужно обработать
USER_IDS = [
    "5464801",
]

# Фильтр по нодам: оставить только эти категории. Пустой список = все ноды.
PREFERRED_NODES = [
    2582, 3974, 3972, 3973, 3175, 3174,
    1000, 1132, 3734, 3173, 3172, 1129,
    1130, 3559, 1355,
]

# Задержка между запросами (секунды), чтобы не получить бан
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
)

SNODS_DIR = Path(os.getenv("SNODS_DIR", "snods"))
DONE_DIR = Path("done")

# Маппинг: заголовок параметра на сайте → ключ в base_form
FIELD_NAMES = {
    "Краткое описание":    "fields[summary][ru]",
    "Подробное описание":  "fields[desc][ru]",
    "Short description":   "fields[summary][en]",
    "Detailed description": "fields[desc][en]",
}

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def make_public_session() -> requests.Session:
    """Сессия без авторизации — для публичных страниц."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_with_retry(
    session: requests.Session,
    url: str,
    cookies: Optional[dict] = None,
    retries: int = 3,
    delay: float = 2.0,
) -> Optional[requests.Response]:
    """GET-запрос с повторными попытками при ошибках сети или 429."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, cookies=cookies, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                print(f"    429 Too Many Requests, жду {delay}с... (попытка {attempt})")
                time.sleep(delay)
                continue
            return response
        except requests.RequestException as exc:
            print(f"    Ошибка сети: {exc} (попытка {attempt}/{retries})")
            time.sleep(delay)
    return None


def get_lot_page(session: requests.Session, lot_id: str, locale: str) -> Optional[BeautifulSoup]:
    """
    Загружает страницу лота в нужной локали.
    Пробует /lots/offer, при 'не найдено' — /chips/offer.
    """
    for endpoint in ("lots", "chips"):
        url = f"https://funpay.com/{endpoint}/offer?id={lot_id}"
        response = fetch_with_retry(session, url, cookies={"locale": locale})
        if response is None:
            return None

        text = response.text
        if "Предложение не найдено" in text or "Offer not found" in text:
            continue  # пробуем chips

        return BeautifulSoup(text, "html.parser")

    return None


def extract_node_id(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает node_id из ссылки «назад» на странице лота."""
    back_link = soup.find("a", class_="js-back-link")
    if not back_link:
        return None
    href = back_link.get("href", "")
    match = re.findall(r"/(\d+)/", href)
    return match[0] if match else None


def extract_price(soup: BeautifulSoup) -> Optional[str]:
    """Извлекает цену из selectpicker на странице лота."""
    select = soup.find("select", class_="selectpicker")
    if not select:
        return None
    option = select.find("option", value="0")
    if not option or not option.get("data-content"):
        return None
    inner = BeautifulSoup(option["data-content"], "html.parser")
    price_tag = inner.find("span", class_="payment-value")
    if not price_tag:
        return None
    price_raw = price_tag.get_text(strip=True)
    match = re.findall(r"[\d]+[.,][\d]+", price_raw)
    return match[0] if match else None


def extract_params(soup: BeautifulSoup, locale: str) -> dict:
    """Извлекает параметры лота (заголовок → значение) из блоков param-item."""
    params = {}
    for item in soup.find_all("div", class_="param-item"):
        title_tag = item.find("h5")
        value_tag = item.find("div", class_="text-bold") or item.find("div")
        if not title_tag or not value_tag:
            continue

        title = title_tag.get_text(strip=True)
        value = value_tag.get_text(strip=True)

        # Пропускаем служебные поля
        skip_titles = {
            "С вашего баланса спишется",
            "Скидка за оплату с баланса",
            "Останется оплатить",
            "Рейтинг продавца",
        }
        if title in skip_titles:
            continue

        if locale == "en":
            # Из английской версии берём только описания
            if title in ("Short description", "Detailed description"):
                params[title] = value
        else:
            params[title] = value

    return params


def parse_lot(session: requests.Session, lot_id: str) -> Optional[dict]:
    """
    Полностью парсит один лот (ru + en локали).

    Returns:
        Словарь с полями лота, или None если лот нужно пропустить.
    """
    details = {}
    node_id = None
    price = None

    for locale in ("ru", "en"):
        soup = get_lot_page(session, lot_id, locale)
        if soup is None:
            print(f"    Не удалось загрузить лот {lot_id} ({locale})")
            return None

        # node_id и цену берём из ru-версии
        if locale == "ru":
            node_id = extract_node_id(soup)
            price = extract_price(soup)

        params = extract_params(soup, locale)

        # Если краткое описание содержит «авто» — это лот с автовыдачей, пропускаем
        if locale == "ru":
            summary = params.get("Краткое описание", "")
            if "авто" in summary.lower():
                print(f"    Лот {lot_id}: автовыдача, пропускаем")
                return None

        details.update(params)
        time.sleep(REQUEST_DELAY)

    if not node_id or not price:
        print(f"    Лот {lot_id}: не удалось определить ноду или цену, пропускаем")
        return None

    details["node_id"] = node_id
    details["price"] = price
    return details


def build_form(details: dict, node_fields: dict) -> dict:
    """
    Составляет base_form из деталей лота и дополнительных полей ноды.

    Args:
        details:     Словарь параметров лота.
        node_fields: Словарь полей ноды из snods/node_*.json.

    Returns:
        Заполненный словарь формы.
    """
    form = {
        "form_created_at": "1763841632",
        "node_id":               details["node_id"],
        "location":              "",
        "deleted":               "",
        "fields[summary][ru]":   "",
        "fields[summary][en]":   "",
        "fields[images]":        "",
        "auto_delivery":         "",
        "price":                 details["price"],
        "amount":                "10000",
        "active":                "on",
        "fields[desc][ru]":      "",
        "fields[desc][en]":      "",
        "fields[payment_msg][ru]": "",
        "fields[payment_msg][en]": "",
        "secrets":               "",
    }

    # Заполняем стандартные текстовые поля
    for field_title, form_key in FIELD_NAMES.items():
        if field_title in details:
            form[form_key] = details[field_title]

    # Заполняем специфичные для ноды поля (select-поля)
    detail_values = set(details.values())
    for field_name, options in node_fields.items():
        for option_text, option_value in options.items():
            if option_text in detail_values:
                form[field_name] = option_value
                break  # нашли совпадение для этого поля — идём дальше

    return form


def load_or_create_node_fields(node_id: str) -> dict:
    """Загружает поля ноды из кэша или парсит их с сайта."""
    path = SNODS_DIR / f"node_{node_id}.json"
    if not path.exists():
        print(f"  Кэш ноды {node_id} не найден, парсим...")
        create_node(node_id)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_lot_ids_from_profile(
    session: requests.Session,
    user_id: str,
    preferred_nodes: list[int],
) -> list[str]:
    """Собирает ID лотов с публичного профиля пользователя."""
    url = f"https://funpay.com/users/{user_id}/"
    response = fetch_with_retry(session, url)
    if response is None:
        print(f"Не удалось загрузить профиль {user_id}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    preferred_str = {str(n) for n in preferred_nodes}
    lot_ids = []

    for offer_block in soup.find_all("div", class_="offer"):
        title_block = offer_block.find("div", class_="offer-list-title")
        if not title_block:
            continue

        link = title_block.find("a")
        if not link:
            continue

        href = link.get("href", "")
        match = re.findall(r"/lots/(\d+)/", href)
        if not match:
            continue

        node_id = match[0]
        if preferred_str and node_id not in preferred_str:
            continue  # нода не в фильтре

        for item in offer_block.find_all("a", class_="tc-item"):
            item_href = item.get("href", "")
            if "id=" in item_href:
                lot_ids.append(item_href.split("id=")[-1])

    return lot_ids


# ---------------------------------------------------------------------------
# Основной скрипт
# ---------------------------------------------------------------------------

def main() -> None:
    SNODS_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)

    session = make_public_session()

    for user_id in USER_IDS:
        print(f"\n{'='*60}")
        print(f"Обрабатываем профиль: {user_id}")
        print(f"{'='*60}")

        lot_ids = get_lot_ids_from_profile(session, user_id, PREFERRED_NODES)
        print(f"Найдено лотов: {len(lot_ids)}")

        output_forms = []

        for lot_id in lot_ids:
            print(f"\nЛот {lot_id}:")

            details = parse_lot(session, lot_id)
            if details is None:
                continue

            node_id = details["node_id"]
            print(f"  Нода: {node_id}, Цена: {details['price']}")

            node_fields = load_or_create_node_fields(node_id)
            form = build_form(details, node_fields)
            output_forms.append(form)

            print(f"  Готово ✓")

        output_path = DONE_DIR / f"profile_{user_id}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output_forms, f, indent=4, ensure_ascii=False)

        print(f"\nСохранено {len(output_forms)} лотов → {output_path}")


if __name__ == "__main__":
    main()
