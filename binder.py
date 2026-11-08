import sys
import ctypes
import tkinter as tk
from ahk_ipc import start_ahk, stop_ahk
from binder_engine import BinderEngine
from gui import BinderGUI


def hide_console():
    """Скрывает окно консоли Windows (CMD) при успешном запуске."""
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd != 0:
        # 0 = SW_HIDE (скрыть окно)
        ctypes.windll.user32.ShowWindow(hwnd, 0)


def main():
    # 1. Запуск AutoHotkey
    if not start_ahk():
        sys.exit(1)

    # 2. Инициализация логики и регистрация хоткеев
    engine = BinderEngine()
    engine.register_hotkeys()

    # 3. Создание GUI окна
    root = tk.Tk()
    gui = BinderGUI(root, engine)

    def on_closing():
        stop_ahk()
        engine.clear_hotkeys()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # 4. Скрываем консоль прямо перед стартом главного цикла интерфейса
    hide_console()
    root.mainloop()


if __name__ == '__main__':
    main()