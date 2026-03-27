# 🚀 FunPay Lots Collector

🌐 **Языки | Languages:**\
[🇷🇺 Русский](#-русская-версия) | [🇬🇧 English](#-english-version)

---

# 🇷🇺 Русская версия

## 🔗 Связанные проекты

- 🤖 Бот: https://github.com/sidor0912/FunPayCardinal
- 🧩 Плагин для создания лотов: https://t.me/fpc_plugins/82
- 🧠 Используется как источник данных для автоматизации

## 📋 Требования

- Python **3.10+**
- Актуальные cookies от аккаунта FunPay
- Установленный и настроенный бот [FunPay Cardinal](https://github.com/sidor0912/FunPayCardinal)

## ⚡ Возможности

- 📦 Парсинг лотов любого профиля FunPay
- 💰 Извлечение цен (включая разные методы оплаты)
- 🧾 Сбор описаний (RU / EN)
- 🧠 Автоматическое сопоставление параметров (node fields)
- 📁 Экспорт в JSON (готовый для использования в боте)
- ⚙️ Работа с несколькими профилями

## 🛠 Установка

### 📥 Способ 1: через Git (рекомендуется)

```bash
git clone https://github.com/fairydarkness/FunpayLotsCollector
cd FunpayLotsCollector
pip install -r requirements.txt
```

### 📦 Способ 2: скачать архив

1. Скачайте проект с GitHub
2. Распакуйте архив
3. Установите зависимости:

```bash
pip install -r requirements.txt
```

## 🍪 Получение cookies

1. Установите расширение [Cookie-Editor](https://cookie-editor.com/) для вашего браузера
2. Войдите в аккаунт на [funpay.com](https://funpay.com)
3. Откройте расширение и найдите куки `golden_key` и `PHPSESSID`
4. Скопируйте их значения в `.env`

## ⚙️ Настройка

Создайте файл `.env` по примеру `.env.example`:

```env
FUNPAY_GOLDEN_KEY=ваш_golden_key
FUNPAY_PHPSESSID=ваш_phpsessid
FUNPAY_USER_IDS=123456,654321

PREFER_LOCALE=ru
REQUEST_TIMEOUT=30
REQUEST_DELAY=0.5
DEFAULT_AMOUNT=10000
DEFAULT_ACTIVE=on
LOGS_DIR=logs
SNODS_DIR=snods
DONE_DIR=done
```

## 🚀 Использование

```bash
python collect_lots.py
```

## 👉 После запуска

- 📥 Получаются все лоты профиля
- 🧠 Обрабатываются параметры
- 📁 Сохраняются в `done/`

## 📤 Использование результата

Собранные JSON-файлы из папки `done/` применяются совместно с плагином для FunPay Cardinal.

### Установка плагина

1. Перейдите по ссылке: https://t.me/fpc_plugins/82
2. Скачайте файл плагина и поместите его в папку `plugins/` вашего FunPay Cardinal

### Создание лотов

1. Запустите бота FunPay Cardinal
2. Отправьте команду `/create_lots` боту в Telegram
3. Прикрепите нужный JSON-файл из папки `done/`
4. Бот автоматически создаст лоты на вашем аккаунте

## 📁 Структура проекта

```
├── collect_lots.py     # основной парсер
├── get_node_data.py    # получение параметров нод
├── getlogs.py          # логгер
├── logs/               # логи
├── snods/              # данные нод
├── done/               # готовые JSON
├── .env
├── .env.example
└── requirements.txt
```

## 🔥 Пример результата

```json
{
    "node_id": "3037",
    "price": "200",
    "fields[summary][ru]": "...",
    "fields[desc][ru]": "...",
    "fields[summary][en]": "...",
    "fields[desc][en]": "..."
}
```

## ⚠️ Важно

❗ Cookies истекают - обновляйте их при ошибках авторизации  
❗ Не злоупотребляйте запросами (есть задержки)  
❗ Возможны изменения HTML FunPay  

## ⭐ Поддержка

Если проект полезен - поставь ⭐  
Связаться / отблагодарить - Telegram [@kortkk](https://t.me/kortkk)

---

# 🇬🇧 English version

## 🔗 Related projects

- 🤖 Bot: https://github.com/sidor0912/FunPayCardinal
- 🧩 Lot creation plugin: https://t.me/fpc_plugins/82
- 🧠 Used as a data source for automation

## 📋 Requirements

- Python **3.10+**
- Valid cookies from your FunPay account
- Installed and configured [FunPay Cardinal](https://github.com/sidor0912/FunPayCardinal) bot

## ⚡ Features

- 📦 Parsing lots from any FunPay profile
- 💰 Extracting prices (including different payment methods)
- 🧾 Collecting descriptions (RU / EN)
- 🧠 Automatic parameter matching (node fields)
- 📁 Export to JSON (ready for use in the bot)
- ⚙️ Working with multiple profiles

## 🛠 Installation

### 📥 Method 1: via Git (recommended)

```bash
git clone https://github.com/fairydarkness/FunpayLotsCollector
cd FunpayLotsCollector
pip install -r requirements.txt
```

### 📦 Method 2: Download the archive

1. Download the project from GitHub (Releases or Code → Download ZIP)
2. Unzip the archive
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## 🍪 Getting cookies

1. Install the [Cookie-Editor](https://cookie-editor.com/) extension for your browser
2. Log in to your account on [funpay.com](https://funpay.com)
3. Open the extension and find `golden_key` and `PHPSESSID` cookies
4. Copy their values into `.env`

## ⚙️ Setup

Create a `.env` file based on `.env.example`:

```env
FUNPAY_GOLDEN_KEY=your_golden_key
FUNPAY_PHPSESSID=your_phpsessid
FUNPAY_USER_IDS=123456,654321

PREFER_LOCALE=ru
REQUEST_TIMEOUT=30
REQUEST_DELAY=0.5
DEFAULT_AMOUNT=10000
DEFAULT_ACTIVE=on
LOGS_DIR=logs
SNODS_DIR=snods
DONE_DIR=done
```

## 🚀 Usage

```bash
python collect_lots.py
```

## 👉 After launch

- 📥 Get all lots from the profile
- 🧠 Process parameters
- 📁 Save in `done/`

## 📤 Using the result

The collected JSON files from the `done/` folder are used together with the FunPay Cardinal plugin.

### Plugin installation

1. Follow the link: https://t.me/fpc_plugins/82
2. Download the plugin file and place it in the `plugins/` folder of your FunPay Cardinal

### Creating lots

1. Launch the FunPay Cardinal bot
2. Send the `/create_lots` command to the bot in Telegram
3. Attach the desired JSON file from the `done/` folder
4. The bot will automatically create lots on your account

## 📁 Project structure

```
├── collect_lots.py     # main parser
├── get_node_data.py    # getting node parameters
├── getlogs.py          # logger
├── logs/               # logs
├── snods/              # node data
├── done/               # finished JSON
├── .env
├── .env.example
└── requirements.txt
```

## 🔥 Example result

```json
{
    "node_id": "3037",
    "price": "200",
    "fields[summary][ru]": "...",
    "fields[desc][ru]": "...",
    "fields[summary][en]": "...",
    "fields[desc][en]": "..."
}
```

## ⚠️ Important

❗ Cookies expire - update them if you get authorization errors  
❗ Avoid excessive requests (delays are in place)  
❗ FunPay HTML structure may change  

## ⭐ Support

If the project is useful, give it a ⭐  
Contact / say thanks - Telegram [@kortkk](https://t.me/kortkk)

---

## 🏷 Keywords

```
funpay parser, funpay scraper, парсер funpay, скрапер funpay, python scraping,
marketplace parser, funpay automation, funpay автоматизация, cardinal addon,
cardinal плагин, cardinal plugin, копирование лотов, copy lots, funpay lots,
funpay лоты, funpay bot, фанпэй парсер, funpay cardinal, funpay export,
экспорт лотов, funpay json, create lots, создание лотов, funpay tools,
game marketplace, игровой маркетплейс, funpay helper, funpay addons, addon
```

## 🔒 Disclaimer

### 🇷🇺

Данный проект предоставлен исключительно в образовательных и исследовательских целях.  
Автор не несёт ответственности за возможное нарушение правил платформы FunPay или любых других сервисов.

Используя данный инструмент, вы самостоятельно несёте ответственность за свои действия, включая:
- соблюдение пользовательских соглашений
- соблюдение законодательства
- корректное использование полученных данных

### 🇬🇧

This project is provided for educational and research purposes only.  
The author is not responsible for any violations of FunPay or other platform rules.

By using this tool, you take full responsibility for your actions, including:
- compliance with platform terms of service
- compliance with applicable laws
- proper use of collected data