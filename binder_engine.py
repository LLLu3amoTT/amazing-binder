import os
import json
import time
import threading
from datetime import datetime
import keyboard
from PIL import ImageGrab
from ahk_ipc import send_to_ahk

SETTINGS_PATH = "settings.json"


class BinderEngine:
    def __init__(self):
        self.config = {
            "screenshot_dir": "raports",
            "binds": [],
            "reports": []
        }
        self.registered_hooks = []
        self.active_report_threads = {}
        self.report_stop_events = {}
        self.load_config()

    def load_config(self):
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.config.update(data)
            except Exception as e:
                print(f"Ошибка чтения settings.json: {e}")

    def save_config(self):
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
        self.register_hotkeys()

    # --- Управление Обычными Биндами ---

    def execute_bind(self, bind_id: str):
        # 1. Принудительно отжимаем системные модификаторы, если они залипли
        for key in ['alt', 'ctrl', 'shift']:
            try:
                keyboard.release(key)
            except Exception:
                pass

        bind_data = next((b for b in self.config.get("binds", []) if b.get("id") == bind_id), None)
        if not bind_data:
            return

        lines = bind_data.get("lines", [])
        try:
            delay = float(bind_data.get("delay", 0.7))
        except ValueError:
            delay = 0.7

        for idx, line in enumerate(lines):
            if not line.strip():
                continue
            send_to_ahk("chat", line)
            if idx < len(lines) - 1 and delay > 0:
                time.sleep(delay)

    def clear_hotkeys(self):
        for hook in self.registered_hooks:
            try:
                keyboard.remove_hotkey(hook)
            except Exception:
                pass
        self.registered_hooks.clear()

    def register_hotkeys(self):
        self.clear_hotkeys()
        for bind in self.config.get("binds", []):
            hk = bind.get("hotkey", "").strip()
            bind_id = bind.get("id")
            if hk and bind_id:
                try:
                    # 2. Вызываем execute_bind в фоновом потоке, 
                    # чтобы time.sleep() не блокировал hook-поток Windows!
                    hook = keyboard.add_hotkey(
                        hk,
                        lambda b_id=bind_id: threading.Thread(
                            target=self.execute_bind, args=(b_id,), daemon=True
                        ).start(),
                        suppress=True
                    )
                    self.registered_hooks.append(hook)
                except Exception as e:
                    print(f"Не удалось зарегистрировать хоткей {hk}: {e}")

    # --- Логика Построчных Авто-Отчетов ---

    def make_screenshot(self, bind_name: str):
        """Создает скриншот с именем формата чч-мм-сс-дд-мм-гггг в выбранной папке."""
        base_dir = self.config.get("screenshot_dir", "raports")
        safe_subfolder = "".join(c for c in bind_name if c.isalnum() or c in (' ', '_', '-')).strip()
        folder_path = os.path.join(base_dir, safe_subfolder if safe_subfolder else "default")
        os.makedirs(folder_path, exist_ok=True)

        # Формат времени: hh-mm-ss-dd-mm-yyyy
        timestamp = datetime.now().strftime("%H-%M-%S-%d-%m-%Y")
        filepath = os.path.join(folder_path, f"{timestamp}.png")
        
        try:
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
            send_to_ahk("local", f"[Биндер] Скриншот сохранен: {filepath}")
        except Exception as e:
            print(f"Ошибка сохранения скриншота: {e}")

    def start_report_loop(self, report_id: str):
        """Запуск цикла отправки отчета."""
        if report_id in self.active_report_threads:
            send_to_ahk("local", "[Биндер] Этот отчёт уже запущен!")
            return

        stop_event = threading.Event()
        self.report_stop_events[report_id] = stop_event

        thread = threading.Thread(
            target=self._report_worker,
            args=(report_id, stop_event),
            daemon=True
        )
        self.active_report_threads[report_id] = thread
        thread.start()

    def stop_report_loop(self, report_id: str):
        """Остановка отчета."""
        if report_id in self.report_stop_events:
            self.report_stop_events[report_id].set()
            self.report_stop_events.pop(report_id, None)
            self.active_report_threads.pop(report_id, None)
            send_to_ahk("local", "[Биндер] Отправка отчёта остановлена.")

    def _report_worker(self, report_id: str, stop_event: threading.Event):
        report_data = next((r for r in self.config.get("reports", []) if r.get("id") == report_id), None)
        if not report_data:
            return

        lines = report_data.get("lines", [])
        if not lines:
            send_to_ahk("local", "[Биндер] В отчёте нет строк для отправки!")
            self.stop_report_loop(report_id)
            return

        bind_name = report_data.get("name", "без_названия")
        try:
            interval_min = float(report_data.get("interval", 10))
        except ValueError:
            interval_min = 10

        interval_sec = int(interval_min * 60)
        total_lines = len(lines)

        send_to_ahk("local", f"[Биндер] Старт отчёта '{bind_name}'. Строк: {total_lines}. Интервал: {interval_min} мин.")

        for idx, line in enumerate(lines):
            if stop_event.is_set():
                break

            if idx > 0:
                wait_time = interval_sec
                
                if wait_time >= 300:
                    notify_advance_sec = 300
                    notify_text = "5 минут"
                elif wait_time >= 120:
                    notify_advance_sec = 60
                    notify_text = "1 минуту"
                else:
                    notify_advance_sec = 0

                if notify_advance_sec > 0 and wait_time > notify_advance_sec:
                    first_wait = wait_time - notify_advance_sec
                    if stop_event.wait(first_wait):
                        break
                    
                    send_to_ahk("local", f"[Внимание] До отправки строки {idx+1}/{total_lines} отчёта '{bind_name}' осталось {notify_text}!")
                    
                    if stop_event.wait(notify_advance_sec):
                        break
                else:
                    if stop_event.wait(wait_time):
                        break

            if stop_event.is_set():
                break

            if line.strip():
                # 1. Отправляем строку в чат
                send_to_ahk("chat", line.strip())
                
                # 2. Ждем 0.2 секунды, чтобы игра успела рендерить строку в чате
                time.sleep(0.8)
                
                # 3. Делаем скриншот с готовым сообщением
                self.make_screenshot(bind_name)
                
                # 4. Выводим локальное уведомление в биндер
                send_to_ahk("local", f"[Биндер] [Отчёт {idx+1}/{total_lines}] Отправлено.")

        if not stop_event.is_set():
            send_to_ahk("local", f"[Биндер] Отчёт '{bind_name}' полностью завершён!")
            self.report_stop_events.pop(report_id, None)
            self.active_report_threads.pop(report_id, None)