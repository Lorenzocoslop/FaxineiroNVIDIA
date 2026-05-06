import os
import sys
import json
import shutil
import time
import logging
import winreg
from pathlib import Path
from datetime import datetime

APPDATA = Path(os.environ.get("APPDATA", Path.home()))
APP_DIR = APPDATA / "FaxineiroNVIDIA"
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "faxineiro.log"
INSTALLED_EXE = APP_DIR / "FaxineiroNVIDIA.exe"

DEFAULT_INTERVAL_SECONDS = 3600
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FaxineiroNVIDIA"


def setup_logging():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
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
    """Copia .exe pra %APPDATA%\FaxineiroNVIDIA\ para ter caminho fixo no startup."""
    current_exe = Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])
    if current_exe.resolve() == INSTALLED_EXE.resolve():
        return  # já rodando do lugar certo
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current_exe, INSTALLED_EXE)
        print(f"App instalado em: {INSTALLED_EXE}")
    except Exception as e:
        print(f"Aviso: não foi possível copiar o app para {APP_DIR}: {e}")


def register_startup():
    """Registra no startup do Windows via Registro."""
    exe_path = str(INSTALLED_EXE)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        print("Registrado no startup do Windows.")
    except Exception as e:
        print(f"Aviso: não foi possível registrar no startup: {e}")


def is_registered_startup() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def detect_default_dxcache() -> str:
    username = os.environ.get("USERNAME", "SeuUsuario")
    return rf"C:\Users\{username}\AppData\Local\NVIDIA\DXCache"


def first_time_setup():
    print("=== Faxineiro NVIDIA - Configuração Inicial ===\n")
    default = detect_default_dxcache()
    print(f"Caminho detectado: {default}")
    path_input = input("Insira o caminho da pasta DXCache (Enter para usar o detectado): ").strip()
    target_path = path_input if path_input else default

    interval_input = input("Intervalo de limpeza em segundos (Enter para 3600 = 1 hora): ").strip()
    try:
        interval = int(interval_input) if interval_input else DEFAULT_INTERVAL_SECONDS
    except ValueError:
        interval = DEFAULT_INTERVAL_SECONDS

    config = {
        "target_path": target_path,
        "interval_seconds": interval,
        "configured_at": datetime.now().isoformat(),
    }
    save_config(config)

    install_to_appdata()
    register_startup()

    print(f"\nConfiguração salva em: {CONFIG_FILE}")
    print(f"Pasta alvo: {target_path}")
    print(f"Intervalo: {interval}s")
    print("Faxineiro NVIDIA vai iniciar automaticamente com o Windows.\n")
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


def main():
    setup_logging()
    config = load_config()

    if not config:
        config = first_time_setup()
    elif not is_registered_startup():
        install_to_appdata()
        register_startup()

    run_loop(config)


if __name__ == "__main__":
    main()
