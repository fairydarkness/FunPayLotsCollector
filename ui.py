"""
ui.py
Простой локальный веб-интерфейс: редактирование .env, запуск collect_lots.py,
просмотр лога и скачивание готовых JSON.

Запуск:
    python ui.py            # http://127.0.0.1:8765
    python ui.py 9000       # другой порт
"""

import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
HTML_PATH = ROOT / "ui.html"

HOST = "127.0.0.1"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


# ---------------------------------------------------------------------------
# Работа с .env
# ---------------------------------------------------------------------------

def parse_env(text: str) -> dict:
    """Разбирает KEY=VALUE строки, игнорируя комментарии."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def read_env() -> dict:
    """Значения из .env поверх значений из .env.example."""
    values = {}
    if ENV_EXAMPLE_PATH.exists():
        values.update(parse_env(ENV_EXAMPLE_PATH.read_text(encoding="utf-8")))
    if ENV_PATH.exists():
        values.update(parse_env(ENV_PATH.read_text(encoding="utf-8")))
    return values


def write_env(new_values: dict) -> None:
    """
    Записывает .env, сохраняя комментарии и порядок строк шаблона
    (существующий .env, иначе .env.example). Новые ключи добавляются в конец.
    """
    if ENV_PATH.exists():
        template = ENV_PATH.read_text(encoding="utf-8")
    elif ENV_EXAMPLE_PATH.exists():
        template = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    else:
        template = ""

    remaining = {k: str(v).replace("\n", " ").strip() for k, v in new_values.items()}
    lines = []
    for line in template.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                lines.append(f"{key}={remaining.pop(key)}")
                continue
        lines.append(line)

    for key, value in remaining.items():
        lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def done_dir() -> Path:
    return ROOT / read_env().get("DONE_DIR", "done")


# ---------------------------------------------------------------------------
# Запуск сканирования
# ---------------------------------------------------------------------------

class Runner:
    """Держит один процесс collect_lots.py и его вывод."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process: subprocess.Popen | None = None
        self.lines: list[str] = []
        self.exit_code: int | None = None

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> bool:
        with self.lock:
            if self.running:
                return False
            self.lines = []
            self.exit_code = None
            env = os.environ.copy()
            env.update(read_env())  # свежие значения из .env имеют приоритет
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            self.process = subprocess.Popen(
                [sys.executable, "collect_lots.py"],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        threading.Thread(target=self._read_output, daemon=True).start()
        return True

    def _read_output(self) -> None:
        process = self.process
        for line in process.stdout:
            self.lines.append(line.rstrip("\n"))
        self.exit_code = process.wait()
        self.lines.append(f"\n--- Процесс завершён, код {self.exit_code} ---")

    def stop(self) -> None:
        with self.lock:
            if self.running:
                self.process.terminate()


runner = Runner()


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass  # не засоряем консоль запросами поллинга

    def _send(self, code: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        url = urlparse(self.path)

        if url.path == "/":
            self._send(200, HTML_PATH.read_bytes(), "text/html; charset=utf-8")

        elif url.path == "/api/env":
            self._json(read_env())

        elif url.path == "/api/status":
            offset = int(parse_qs(url.query).get("offset", ["0"])[0])
            self._json({
                "running": runner.running,
                "exit_code": runner.exit_code,
                "lines": runner.lines[offset:],
                "offset": len(runner.lines),
            })

        elif url.path == "/api/results":
            folder = done_dir()
            files = []
            if folder.exists():
                for path in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                    try:
                        count = len(json.loads(path.read_text(encoding="utf-8")))
                    except (ValueError, TypeError):
                        count = None
                    files.append({
                        "name": path.name,
                        "size": path.stat().st_size,
                        "mtime": path.stat().st_mtime,
                        "count": count,
                    })
            self._json(files)

        elif url.path.startswith("/api/results/"):
            name = Path(unquote(url.path.removeprefix("/api/results/"))).name
            path = done_dir() / name
            if not path.is_file():
                self._json({"error": "not found"}, 404)
                return
            self._send(200, path.read_bytes(), "application/json; charset=utf-8",
                       {"Content-Disposition": f'attachment; filename="{name}"'})

        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/api/env":
            write_env(self._read_json())
            self._json({"ok": True})

        elif self.path == "/api/run":
            if runner.start():
                self._json({"ok": True})
            else:
                self._json({"ok": False, "error": "Сканирование уже идёт"}, 409)

        elif self.path == "/api/stop":
            runner.stop()
            self._json({"ok": True})

        else:
            self._json({"error": "not found"}, 404)


def main() -> None:
    # Только localhost: в .env лежат куки аккаунта
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"UI запущен: {url}  (Ctrl+C для выхода)")
    threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runner.stop()
        server.server_close()


if __name__ == "__main__":
    main()
