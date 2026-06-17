#!/usr/bin/env python3
"""KALF 시스템 트레이 앱."""
import ctypes
import os
import sys
import subprocess
import threading

import httpx
import pystray
from PIL import Image, ImageDraw
from dotenv import load_dotenv


# ── 단일 인스턴스 보장 ────────────────────────────────────────────────────

def _ensure_single_instance():
    """Windows 뮤텍스로 중복 실행 방지. 이미 실행 중이면 조용히 종료."""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\KALF_TrayApp_Mutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)
    return mutex  # GC 방지용 — 전역에서 참조 유지


_mutex = _ensure_single_instance()


# ── 경로 처리 ─────────────────────────────────────────────────────────────

def resource_path(relative_path: str) -> str:
    """PyInstaller 패키징 시 _MEIPASS 기반 절대경로 반환."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


PROJECT_DIR = r"C:\Users\wodhk\Desktop\Learning"
TRAY_DIR = os.path.dirname(os.path.abspath(__file__))

_env_path = (
    resource_path(".env")
    if hasattr(sys, "_MEIPASS")
    else os.path.join(PROJECT_DIR, ".env")
)
load_dotenv(_env_path)

_vault_raw = os.getenv("VAULT_PATH", "./obsidian_vault")
VAULT_PATH: str = os.path.normpath(os.path.join(PROJECT_DIR, _vault_raw))

LOG_FILE = os.path.join(TRAY_DIR, "kalf.log")
HEALTH_URL = "http://localhost:8000/health"
POLL_INTERVAL = 5  # seconds


# ── 아이콘 ────────────────────────────────────────────────────────────────

def _make_circle_icon(color: tuple) -> Image.Image:
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([2, 2, 30, 30], fill=color)
    return img


def _load_icon(filename: str, fallback_color: tuple) -> Image.Image:
    if hasattr(sys, "_MEIPASS"):
        path = os.path.join(sys._MEIPASS, "tray", filename)
    else:
        path = os.path.join(TRAY_DIR, filename)
    if os.path.exists(path):
        return Image.open(path).convert("RGBA")
    return _make_circle_icon(fallback_color)


# ── 트레이 앱 ─────────────────────────────────────────────────────────────

class KALFTray:
    def __init__(self) -> None:
        self._server_proc: subprocess.Popen | None = None
        self._server_running = False
        self._icon: pystray.Icon | None = None
        self._stop_event = threading.Event()

        self._img_green = _load_icon("icon_green.png", (76, 175, 80, 255))
        self._img_gray = _load_icon("icon_gray.png", (158, 158, 158, 255))

    # ── 메뉴 ──────────────────────────────────────────────────────────────

    def _status_text(self, item) -> str:
        return "KALF - 실행 중" if self._server_running else "KALF - 중지됨"

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("서버 시작", self._on_start),
            pystray.MenuItem("서버 중지", self._on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Obsidian 열기", self._on_open_obsidian),
            pystray.MenuItem("로그 보기", self._on_open_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._on_quit),
        )

    # ── 서버 시작 ─────────────────────────────────────────────────────────

    def _on_start(self, icon: pystray.Icon, item) -> None:
        if self._server_proc and self._server_proc.poll() is None:
            icon.notify("이미 실행 중입니다", "KALF")
            return
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as log_fd:
                self._server_proc = subprocess.Popen(
                    [
                        "uvicorn", "backend.main:app",
                        "--host", "0.0.0.0", "--port", "8000",
                    ],
                    cwd=PROJECT_DIR,
                    stdout=log_fd,
                    stderr=log_fd,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            icon.notify("서버를 시작했습니다", "KALF")
        except Exception as exc:
            icon.notify(f"서버 시작 실패: {exc}", "KALF")

    # ── 서버 중지 ─────────────────────────────────────────────────────────

    def _on_stop(self, icon: pystray.Icon, item) -> None:
        if self._server_proc:
            try:
                self._server_proc.terminate()
                self._server_proc.wait(timeout=5)
            except Exception:
                pass
            self._server_proc = None

        subprocess.run(
            ["taskkill", "/F", "/IM", "uvicorn.exe"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self._server_running = False
        if self._icon:
            self._icon.icon = self._img_gray
        icon.notify("서버를 중지했습니다", "KALF")

    # ── Obsidian 열기 ─────────────────────────────────────────────────────

    def _on_open_obsidian(self, icon: pystray.Icon, item) -> None:
        vault_name = os.path.basename(VAULT_PATH)
        try:
            os.startfile(f"obsidian://open?vault={vault_name}")
        except Exception as exc:
            icon.notify(f"Obsidian 열기 실패: {exc}", "KALF")

    # ── 로그 보기 ─────────────────────────────────────────────────────────

    def _on_open_log(self, icon: pystray.Icon, item) -> None:
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", encoding="utf-8"):
                pass
        subprocess.Popen(
            ["notepad.exe", LOG_FILE],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    # ── 종료 ──────────────────────────────────────────────────────────────

    def _on_quit(self, icon: pystray.Icon, item) -> None:
        self._stop_event.set()
        self._on_stop(icon, item)
        icon.stop()

    # ── 상태 폴링 (백그라운드 스레드) ────────────────────────────────────

    def _poll_health(self) -> None:
        while True:
            try:
                resp = httpx.get(HEALTH_URL, timeout=3.0)
                is_up = resp.status_code == 200
            except Exception:
                is_up = False

            if is_up != self._server_running:
                self._server_running = is_up
                if self._icon:
                    self._icon.icon = self._img_green if is_up else self._img_gray

            if self._stop_event.wait(POLL_INTERVAL):
                break

    # ── 실행 ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        threading.Thread(target=self._poll_health, daemon=True).start()
        self._icon = pystray.Icon(
            "KALF",
            self._img_gray,
            "KALF",
            menu=self._build_menu(),
        )
        self._icon.run()


if __name__ == "__main__":
    KALFTray().run()
