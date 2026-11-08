import os
import time
import subprocess
import ctypes
import ctypes.wintypes

AHK_PATH = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
AHK_DIR = "AHK"
SCRIPT_PATH = os.path.join(AHK_DIR, "sender.ahk")

ahk_process = None


class COPYDATASTRUCT(ctypes.Structure):
    _fields_ = [
        ('dwData', ctypes.wintypes.LPARAM),
        ('cbData', ctypes.wintypes.DWORD),
        ('lpData', ctypes.c_void_p)
    ]


def start_ahk() -> bool:
    global ahk_process
    if not os.path.exists(AHK_PATH):
        print(f"[ОШИБКА] Не найден AHK по пути: {AHK_PATH}")
        return False
    if not os.path.exists(SCRIPT_PATH):
        print(f"[ОШИБКА] Не найден скрипт: {SCRIPT_PATH}")
        return False

    try:
        ahk_process = subprocess.Popen([AHK_PATH, SCRIPT_PATH])
        time.sleep(0.4)
        return True
    except Exception as e:
        print(f"[ОШИБКА] Ошибка запуска AHK: {e}")
        return False


def stop_ahk():
    global ahk_process
    if ahk_process and ahk_process.poll() is None:
        ahk_process.terminate()


def send_to_ahk(action: str, text: str) -> bool:
    hwnd = ctypes.windll.user32.FindWindowW(None, "AmazingBinderAHKReceiver")
    if not hwnd:
        return False

    message = f"{action}|{text}"
    encoded = message.encode('cp1251', errors='ignore')

    # ВАЖНО: сохраняем буфер в переменную buf, чтобы GC не удалил его до передачи в AHK!
    buf = ctypes.create_string_buffer(encoded)

    cds = COPYDATASTRUCT()
    cds.dwData = 0
    cds.cbData = len(encoded) + 1
    cds.lpData = ctypes.cast(buf, ctypes.c_void_p)

    ctypes.windll.user32.SendMessageW(hwnd, 0x004A, 0, ctypes.byref(cds))
    return True