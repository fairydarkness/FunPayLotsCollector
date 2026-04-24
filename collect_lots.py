import json
import os
from pathlib import Path
from typing import Dict

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://funpay.com"
SNODS_DIR = Path(os.getenv("SNODS_DIR", "snods"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.cookies.update(
        {
            "golden_key": _require_env("FUNPAY_GOLDEN_KEY"),
            "PHPSESSID": _require_env("FUNPAY_PHPSESSID"),
            "locale": "ru",
        }
    )
    return session


def parse_selects(html: str) -> Dict[str, Dict[str, str]]:
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


def get_node_fields(node_id: str | int) -> Dict[str, Dict[str, str]]:
    node_id = str(node_id)
    session = build_session()

    try:
        url = f"{BASE_URL}/lots/offerEdit?node={node_id}"
        print(f"Парсим: {url}")

        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        return parse_selects(response.text)

    finally:
        session.close()


def create_node(node_id: str | int) -> None:
    node_id = str(node_id)

    SNODS_DIR.mkdir(parents=True, exist_ok=True)

    result = get_node_fields(node_id)

    path = SNODS_DIR / f"node_{node_id}.json"

    with path.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)

    print(f"Сохранено: {path} ({len(result)} полей)")
