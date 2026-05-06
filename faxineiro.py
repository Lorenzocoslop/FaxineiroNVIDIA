import os
import sys
import json
import shutil
import time
import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw
import pystray

try:
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False

APPDATA = Path(os.environ.get("APPDATA", Path.home()))
APP_DIR = APPDATA / "FaxineiroNVIDIA"
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "faxineiro.log"
INSTALLED_EXE = APP_DIR / "FaxineiroNVIDIA.exe"
INSTALLED_UNINSTALL_EXE = APP_DIR / "Uninstall.exe"

DEFAULT_INTERVAL_SECONDS = 3600
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FaxineiroNVIDIA"
APP_NAME = "FaxineiroNVIDIA"

tray_icon = None


def setup_logging():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def install_to_appdata():
    if not WINDOWS:
        return
    current_exe = Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if current_exe.resolve() != INSTALLED_EXE.resolve():
            shutil.copy2(current_exe, INSTALLED_EXE)
        uninstall_src = current_exe.parent / "Uninstall.exe"
        if uninstall_src.exists() and uninstall_src.resolve() != INSTALLED_UNINSTALL_EXE.resolve():
            shutil.copy2(uninstall_src, INSTALLED_UNINSTALL_EXE)
    except Exception:
        pass


def register_startup():
    if not WINDOWS:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{INSTALLED_EXE}"')
    except Exception:
        pass


def register_uninstall():
    if not WINDOWS:
        return
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Faxineiro NVIDIA")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{INSTALLED_UNINSTALL_EXE}"')
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(INSTALLED_EXE))
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(APP_DIR))
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "FaxineiroNVIDIA")
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass


def is_registered_startup() -> bool:
    if not WINDOWS:
        return True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def detect_default_dxcache() -> str:
    username = os.environ.get("USERNAME", os.environ.get("USER", "Usuario"))
    if WINDOWS:
        return rf"C:\Users\{username}\AppData\Local\NVIDIA\DXCache"
    return str(Path.home() / "NVIDIA" / "DXCache")


def make_tray_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=(118, 185, 0, 255))
    draw.text((18, 18), "FX", fill=(255, 255, 255, 255))
    return img


def first_time_setup():
    root = tk.Tk()
    root.withdraw()

    default = detect_default_dxcache()

    messagebox.showinfo(
        "Faxineiro NVIDIA",
        "Bem-vindo! Selecione a pasta DXCache da NVIDIA para limpeza automática.\n\n"
        f"Padrão detectado:\n{default}"
    )

    chosen = filedialog.askdirectory(
        title="Selecione a pasta DXCache",
        initialdir=str(Path(default).parent) if Path(default).parent.exists() else str(Path.home()),
    )
    target_path = chosen if chosen else default

    interval_str = simpledialog.askstring(
        "Intervalo",
        "Intervalo de limpeza em segundos:\n(padrão: 3600 = 1 hora)",
        initialvalue="3600",
        parent=root,
    )
    try:
        interval = int(interval_str) if interval_str else DEFAULT_INTERVAL_SECONDS
    except (ValueError, TypeError):
        interval = DEFAULT_INTERVAL_SECONDS

    config = {
        "target_path": target_path,
        "interval_seconds": interval,
        "configured_at": datetime.now().isoformat(),
    }
    save_config(config)
    install_to_appdata()
    register_startup()
    register_uninstall()

    messagebox.showinfo(
        "Faxineiro NVIDIA",
        f"Configurado!\n\nPasta: {target_path}\nIntervalo: {interval}s\n\n"
        "O app vai rodar em segundo plano e iniciar automaticamente com o Windows."
    )

    root.destroy()
    return config


def clean_directory(target_path: str) -> tuple[int, int]:
    path = Path(target_path)
    deleted = 0
    skipped = 0

    if not path.exists():
        logging.warning(f"Pasta não encontrada: {target_path}")
        return 0, 0

    for item in list(path.iterdir()):
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            deleted += 1
            logging.info(f"Deletado: {item.name}")
        except PermissionError:
            skipped += 1
            logging.debug(f"Sem permissão (ignorado): {item.name}")
        except Exception as e:
            skipped += 1
            logging.debug(f"Erro ao deletar {item.name}: {e}")

    return deleted, skipped


def run_loop(config: dict):
    target = config["target_path"]
    interval = config["interval_seconds"]
    logging.info(f"Faxineiro NVIDIA iniciado. Alvo: {target} | Intervalo: {interval}s")

    while True:
        logging.info("Iniciando limpeza...")
        deleted, skipped = clean_directory(target)
        logging.info(f"Limpeza concluída: {deleted} deletados, {skipped} ignorados.")
        time.sleep(interval)


def on_clean_now(icon, item):
    config = load_config()
    deleted, skipped = clean_directory(config["target_path"])
    icon.notify(f"Limpeza concluída: {deleted} deletados, {skipped} ignorados.", "Faxineiro NVIDIA")


def on_open_log(icon, item):
    os.startfile(str(LOG_FILE))


def on_uninstall(icon, item):
    if INSTALLED_UNINSTALL_EXE.exists():
        os.startfile(str(INSTALLED_UNINSTALL_EXE))
    else:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro", f"Uninstall.exe não encontrado em:\n{INSTALLED_UNINSTALL_EXE}")
        root.destroy()


def on_quit(icon, item):
    icon.stop()
    os._exit(0)


def start_tray(config: dict):
    global tray_icon
    image = make_tray_image()
    menu = pystray.Menu(
        pystray.MenuItem("Faxineiro NVIDIA", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Limpar agora", on_clean_now),
        pystray.MenuItem("Ver log", on_open_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Desinstalar", on_uninstall),
        pystray.MenuItem("Sair", on_quit),
    )
    tray_icon = pystray.Icon(APP_NAME, image, "Faxineiro NVIDIA", menu)

    loop_thread = threading.Thread(target=run_loop, args=(config,), daemon=True)
    loop_thread.start()

    tray_icon.run()


def main():
    setup_logging()
    config = load_config()

    if not config:
        config = first_time_setup()
    elif not is_registered_startup():
        install_to_appdata()
        register_startup()

    start_tray(config)


if __name__ == "__main__":
    main()
