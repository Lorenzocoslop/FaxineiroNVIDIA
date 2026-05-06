import os
import sys
import shutil
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

try:
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False

APPDATA = Path(os.environ.get("APPDATA", Path.home()))
APP_DIR = APPDATA / "FaxineiroNVIDIA"
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FaxineiroNVIDIA"
APP_NAME = "FaxineiroNVIDIA"


def remove_registry_key(hive, key_path):
    try:
        winreg.DeleteKey(hive, key_path)
    except Exception:
        pass


def remove_registry_value(hive, key_path, value_name):
    try:
        with winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, value_name)
    except Exception:
        pass


def main():
    root = tk.Tk()
    root.withdraw()

    confirm = messagebox.askyesno(
        "Desinstalar Faxineiro NVIDIA",
        "Tem certeza que deseja desinstalar o Faxineiro NVIDIA?\n\n"
        "Isso vai:\n"
        "- Remover o app do startup do Windows\n"
        "- Remover da lista de aplicativos instalados\n"
        "- Apagar configurações e logs",
    )

    if not confirm:
        root.destroy()
        return

    if WINDOWS:
        os.system("taskkill /f /im FaxineiroNVIDIA.exe >nul 2>&1")
        remove_registry_value(winreg.HKEY_CURRENT_USER, STARTUP_KEY, APP_NAME)
        remove_registry_key(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)

    try:
        shutil.rmtree(APP_DIR)
    except Exception:
        pass

    messagebox.showinfo(
        "Desinstalado",
        "Faxineiro NVIDIA foi removido com sucesso.",
    )
    root.destroy()
    os._exit(0)


if __name__ == "__main__":
    main()
