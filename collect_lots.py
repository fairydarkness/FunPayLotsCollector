import json
import os
import re
import time
from pathlib import Path
from typing import Any

from getlogs import logger

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from get_node_data import create_node

load_dotenv()

BASE_URL = "https://funpay.com"
HEADERS = {
    "User-Agent": os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )
}
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))
PREFER_LOCALE = os.getenv("PREFER_LOCALE", "ru")
PROFILE_IDS = [item.strip() for item in os.getenv("FUNPAY_USER_IDS", "").split(",") if item.strip()]
SNODS_DIR = Path(os.getenv("SNODS_DIR", "snods"))
OUTPUT_DIR = Path(os.getenv("DONE_DIR", "done"))
NODE_IDS_FILE = Path(os.getenv("NODE_IDS_FILE", "node_ids.json"))


NAMES_MAP = {
    "Краткое описание": "fields[summary][ru]",
    "Подробное описание": "fields[desc][ru]",
    "Short description": "fields[summary][en]",
    "Detailed description": "fields[desc][en]",
}

IGNORE_FIELDS_RU = {
    "С вашего баланса спишется",
    "Скидка за оплату с баланса",
    "Останется оплатить",
    "Рейтинг продавца",
    "С вашего баланса спишется ",
}


def ensure_directories() -> None:
    SNODS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    NODE_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)



def build_base_form() -> dict[str, Any]:
    return {
        "form_created_at": os.getenv("FORM_CREATED_AT", "0"),
        "node_id": "",
        "location": "",
        "deleted": "",
        "fields[summary][ru]": "",
        "fields[summary][en]": "",
        "fields[images]": "",
        "auto_delivery": "",
        "price": "",
        "amount": os.getenv("DEFAULT_AMOUNT", "10000"),
        "active": os.getenv("DEFAULT_ACTIVE", "on"),
        "fields[desc][ru]": "",
        "fields[desc][en]": "",
        "fields[payment_msg][ru]": "",
        "fields[payment_msg][en]": "",
        "secrets": "",
    }



def read_node_ids() -> list[str]:
    if not NODE_IDS_FILE.exists():
        return []
    with NODE_IDS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("node_ids.json must contain a JSON list")
    return [str(item) for item in data]



def write_node_ids(node_ids: list[str]) -> None:
    unique_ids = sorted(set(node_ids), key=lambda x: int(x) if x.isdigit() else x)
    with NODE_IDS_FILE.open("w", encoding="utf-8") as file:
        json.dump(unique_ids, file, indent=4, ensure_ascii=False)



def fetch(url: str, *, cookies: dict[str, str] | None = None) -> requests.Response:
    response = requests.get(url, headers=HEADERS, cookies=cookies, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response



def extract_lot_ids(profile_id: str) -> list[str]:
    response = fetch(f"{BASE_URL}/users/{profile_id}/")
    soup = BeautifulSoup(response.text, "html.parser")

    lot_ids: list[str] = []
    for item in soup.find_all("a", class_="tc-item"):
        href = item.get("href", "")
        if "id=" in href:
            lot_ids.append(href.split("id=")[-1])
    return lot_ids



def parse_offer_page(lot_id: str, locale: str) -> BeautifulSoup | None:
    attempts = 3
    while attempts:
        try:
            cookies = {"locale": locale}
            response = fetch(f"{BASE_URL}/lots/offer?id={lot_id}", cookies=cookies)
            if response.status_code == 429 or "429" in response.text[0:300]:
                raise Exception
            if "Предложение не найдено" in response.text or "Offer not found" in response.text:
                response = fetch(f"{BASE_URL}/chips/offer?id={lot_id}", cookies=cookies)
                if "Предложение не найдено" in response.text or "Offer not found" in response.text:
                    return None
            return BeautifulSoup(response.text, "html.parser")
        except:
            time.sleep(1)
            attempts -= 1

    logger.info(f"Не удалось обработать лот {lot_id} | Failed to process lot {lot_id}")
    return None



def extract_node_id(soup: BeautifulSoup) -> str | None:
    back_link = soup.find("a", class_="js-back-link")
    category_url = back_link.get("href") if back_link else None
    if not category_url:
        return None
    match = re.search(r"/(\d+)/", category_url)
    return match.group(1) if match else None



def extract_price(soup: BeautifulSoup) -> str | None:
    filter_option = soup.find("select", class_="selectpicker")
    if not filter_option:
        return None

    option = filter_option.find("option", value="0")
    if not option or not option.get("data-content"):
        return None

    inner = BeautifulSoup(option["data-content"], "html.parser")
    price_tag = inner.find("span", class_="payment-value")
    if not price_tag:
        return None

    price_raw = price_tag.get_text(strip=True)
    match = re.search(r"([0-9]+[.,0-9]*)", price_raw)
    return match.group(1) if match else None



def extract_details(soup: BeautifulSoup, locale: str) -> dict[str, str]:
    details: dict[str, str] = {}
    for item in soup.find_all("div", class_="param-item"):
        title = item.find("h5")
        value = item.find("div", class_="text-bold") or item.find("div")
        if not title or not value:
            continue

        title_text = title.get_text(strip=True)
        value_text = value.get_text(strip=True)

        if locale == "en":
            if title_text in ("Short description", "Detailed description"):
                details[title_text] = value_text
            continue

        if title_text in IGNORE_FIELDS_RU:
            continue

        details[title_text] = value_text
    return details



def ensure_node_data(node_id: str) -> Path:
    path = SNODS_DIR / f"node_{node_id}.json"
    if not path.exists():
        logger.info(f"Отсутствует нода, создаем: {node_id} | Node data missing, creating: {node_id}")
        create_node(node_id)
    return path



def map_additional_fields(base_form: dict[str, Any], details: dict[str, str], node_id: str) -> None:
    path = ensure_node_data(node_id)
    with path.open("r", encoding="utf-8") as file:
        additional_fields = json.load(file)

    values = list(details.values())
    for field, options in additional_fields.items():
        for text_value, option_value in options.items():
            if text_value in values:
                base_form[field] = option_value



def process_lot(lot_id: str, node_ids: list[str]) -> dict[str, Any] | None:
    logger.info(f"Обрабатываю лот {lot_id} | Processing lot {lot_id}")

    base_form = build_base_form()
    details: dict[str, str] = {}
    node_id: str | None = None
    price: str | None = None

    for locale in ("en", "ru"):
        soup = parse_offer_page(lot_id, locale)

        if not soup:
            break

        if node_id is None:
            node_id = extract_node_id(soup)
        if price is None and locale == PREFER_LOCALE:
            price = extract_price(soup)

        details.update(extract_details(soup, locale))
        time.sleep(REQUEST_DELAY)

    if not node_id:
        logger.warning(f"Пропускаю лот {lot_id}: не удалось извлечь node_id | Skipping lot {lot_id}: failed to extract node_id")
        return None

    if not price:
        logger.warning(
            f"Пропускаю лот {lot_id}: не удалось извлечь цену | Skipping lot {lot_id}: failed to extract price")

    for source_name, target_name in NAMES_MAP.items():
        if source_name in details:
            base_form[target_name] = details.pop(source_name)

    base_form["node_id"] = node_id
    base_form["price"] = price

    node_ids.append(node_id)
    write_node_ids(node_ids)
    map_additional_fields(base_form, details, node_id)

    return base_form

ensure_directories()

if not PROFILE_IDS:
    raise RuntimeError("FUNPAY_USER_IDS пуст. Заполните его в .env или переменных окружения | FUNPAY_USER_IDS is empty. Fill it in .env or environment variables.")

existing_node_ids = read_node_ids()

for profile_id in PROFILE_IDS:
    output_forms = None
    try:
        lot_ids = extract_lot_ids(profile_id)
        logger.info(f"Найдено {len(lot_ids)} лотов в профиле {profile_id} | Found {len(lot_ids)} lots in profile {profile_id}")

        output_forms: list[dict[str, Any]] | None = []
        for lot_id in lot_ids:
            form = process_lot(lot_id, existing_node_ids)

            if form is not None:
                output_forms.append(form)
    except:
        logger.info("Выполнение прервано, сохраняю удачные лоты | Execution interrupted, saving successful lots")
        logger.debug("TRACEBACK", exc_info=True)
    finally:
        if output_forms:
            output_file = OUTPUT_DIR / f"profile_{profile_id}.json"
            with output_file.open("w", encoding="utf-8") as file:
                json.dump(output_forms, file, indent=4, ensure_ascii=False)

            logger.info(f"Сохранено {len(output_forms)} лотов в {output_file} | Saved {len(output_forms)} lots to {output_file}")