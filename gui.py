import uuid
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from binder_engine import BinderEngine


def attach_context_menu(widget):
    menu = tk.Menu(widget, tearoff=0)
    
    def cut():
        widget.event_generate("<<Cut>>")
    def copy():
        widget.event_generate("<<Copy>>")
    def paste():
        widget.event_generate("<<Paste>>")
    def select_all():
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end")
        elif isinstance(widget, (ttk.Entry, tk.Entry)):
            widget.select_range(0, tk.END)

    menu.add_command(label="Вырезать", command=cut)
    menu.add_command(label="Копировать", command=copy)
    menu.add_command(label="Вставить", command=paste)
    menu.add_separator()
    menu.add_command(label="Выделить всё", command=select_all)

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_menu)
    
    widget.bind("<Control-a>", lambda e: (select_all(), "break")[1])
    widget.bind("<Control-A>", lambda e: (select_all(), "break")[1])
    widget.bind("<Control-c>", lambda e: (copy(), "break")[1])
    widget.bind("<Control-C>", lambda e: (copy(), "break")[1])
    widget.bind("<Control-v>", lambda e: (paste(), "break")[1])
    widget.bind("<Control-V>", lambda e: (paste(), "break")[1])
    widget.bind("<Control-x>", lambda e: (cut(), "break")[1])
    widget.bind("<Control-X>", lambda e: (cut(), "break")[1])


class HotkeyRecorderButton(ttk.Button):
    def __init__(self, parent, initial_hotkey="", **kwargs):
        super().__init__(parent, **kwargs)
        self.hotkey = initial_hotkey
        self.is_recording = False
        self.pressed_keys = set()
        self.update_text()
        self.config(command=self.start_recording)

    def update_text(self):
        if self.is_recording:
            self.config(text="[ Нажмите клавиши... (Esc - Сброс) ]")
        else:
            self.config(text=self.hotkey.upper() if self.hotkey else "Не назначено (Нажмите для выбора)")

    def start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.pressed_keys.clear()
        self.update_text()
        top = self.winfo_toplevel()
        top.bind("<KeyPress>", self.on_key_press)
        top.bind("<KeyRelease>", self.on_key_release)

    def stop_recording(self):
        self.is_recording = False
        top = self.winfo_toplevel()
        top.unbind("<KeyPress>")
        top.unbind("<KeyRelease>")
        self.update_text()

    def on_key_press(self, event):
        if not self.is_recording:
            return "break"
        keysym = event.keysym.lower()
        if keysym == "escape":
            self.hotkey = ""
            self.stop_recording()
            return "break"

        mod_map = {
            "control_l": "ctrl", "control_r": "ctrl",
            "alt_l": "alt", "alt_r": "alt",
            "shift_l": "shift", "shift_r": "shift",
            "win_l": "windows", "win_r": "windows"
        }
        key_name = mod_map.get(keysym, keysym)
        if len(key_name) == 1:
            key_name = key_name.lower()

        self.pressed_keys.add(key_name)
        modifiers = {"ctrl", "alt", "shift", "windows"}
        non_mods = [k for k in self.pressed_keys if k not in modifiers]

        if non_mods:
            ordered_mods = [k for k in ["ctrl", "alt", "shift", "windows"] if k in self.pressed_keys]
            self.hotkey = "+".join(ordered_mods + non_mods)
            self.stop_recording()

        return "break"

    def on_key_release(self, event):
        return "break"

    def get_hotkey(self):
        return self.hotkey

    def set_hotkey(self, hk):
        self.hotkey = hk
        self.update_text()


class BinderGUI:
    def __init__(self, root, engine: BinderEngine):
        self.root = root
        self.engine = engine
        self.root.title("Amazing Binder")
        self.root.geometry("820x620")

        self.bind_tabs_map = {}
        self.report_tabs_map = {}

        self.create_main_layout()
        self.load_all_from_config()

    def create_main_layout(self):
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tab_binds = ttk.Frame(self.main_notebook)
        self.tab_reports = ttk.Frame(self.main_notebook)

        self.main_notebook.add(self.tab_binds, text="  Бинды  ")
        self.main_notebook.add(self.tab_reports, text="  Отчёты  ")

        # --- Панель обычных биндов ---
        binds_top_bar = ttk.Frame(self.tab_binds, padding=5)
        binds_top_bar.pack(fill=tk.X)

        btn_add_bind = ttk.Button(binds_top_bar, text="+ Добавить бинд", command=self.add_new_bind_tab)
        btn_add_bind.pack(side=tk.LEFT, padx=5)

        btn_save_binds = ttk.Button(binds_top_bar, text="Сохранить и Применить", command=self.save_all)
        btn_save_binds.pack(side=tk.RIGHT, padx=5)

        self.binds_notebook = ttk.Notebook(self.tab_binds)
        self.binds_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Панель отчётов ---
        reports_top_bar = ttk.Frame(self.tab_reports, padding=5)
        reports_top_bar.pack(fill=tk.X)

        btn_add_report = ttk.Button(reports_top_bar, text="+ Добавить отчёт", command=self.add_new_report_tab)
        btn_add_report.pack(side=tk.LEFT, padx=5)

        btn_save_reports = ttk.Button(reports_top_bar, text="Сохранить настройки отчётов", command=self.save_all)
        btn_save_reports.pack(side=tk.RIGHT, padx=5)

        # Панель выбора общей папки скриншотов
        path_frame = ttk.Frame(self.tab_reports, padding=5)
        path_frame.pack(fill=tk.X, padx=5)

        ttk.Label(path_frame, text="Папка сохранения скриншотов:").pack(side=tk.LEFT, padx=(0, 5))
        self.dir_entry = ttk.Entry(path_frame, width=45)
        self.dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        attach_context_menu(self.dir_entry)

        btn_browse = ttk.Button(path_frame, text="Обзор...", command=self.browse_dir)
        btn_browse.pack(side=tk.LEFT, padx=5)

        self.reports_notebook = ttk.Notebook(self.tab_reports)
        self.reports_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def browse_dir(self):
        selected_folder = filedialog.askdirectory()
        if selected_folder:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, selected_folder)

    # --- Вкладки обычных Биндов ---

    def add_bind_tab(self, bind_id: str, title: str, hotkey: str, delay: str, lines: list):
        tab = ttk.Frame(self.binds_notebook, padding=10)
        self.binds_notebook.add(tab, text=title)

        ttk.Label(tab, text="Горячая клавиша:").pack(anchor=tk.W)
        hk_btn = HotkeyRecorderButton(tab, initial_hotkey=hotkey)
        hk_btn.pack(anchor=tk.W, pady=(3, 10))

        ttk.Label(tab, text="Задержка между строками (сек):").pack(anchor=tk.W)
        delay_entry = ttk.Entry(tab, width=15)
        delay_entry.insert(0, delay)
        delay_entry.pack(anchor=tk.W, pady=(3, 10))
        attach_context_menu(delay_entry)

        ttk.Label(tab, text="Текст сообщений (каждая строка — отдельная команда):").pack(anchor=tk.W)
        text_area = tk.Text(tab, height=10, width=75)
        text_area.insert("1.0", "\n".join(lines))
        text_area.pack(fill=tk.BOTH, expand=True, pady=(3, 10))
        attach_context_menu(text_area)

        btn_del = ttk.Button(tab, text="Удалить этот бинд", command=lambda b_id=bind_id: self.delete_bind_tab(b_id))
        btn_del.pack(anchor=tk.E)

        self.bind_tabs_map[bind_id] = {
            "tab": tab,
            "hk_btn": hk_btn,
            "delay": delay_entry,
            "text": text_area
        }

    def add_new_bind_tab(self):
        new_id = f"bind_{uuid.uuid4().hex[:6]}"
        count = len(self.bind_tabs_map) + 1
        self.add_bind_tab(new_id, f"Бинд #{count}", "", "0.7", [])

    def delete_bind_tab(self, bind_id: str):
        if bind_id in self.bind_tabs_map:
            tab = self.bind_tabs_map[bind_id]["tab"]
            self.binds_notebook.forget(tab)
            del self.bind_tabs_map[bind_id]

    # --- Вкладки Отчётов ---

    def add_report_tab(self, report_id: str, name: str, interval: str, lines: list):
        tab = ttk.Frame(self.reports_notebook, padding=10)
        self.reports_notebook.add(tab, text=name if name else "Новый отчёт")

        ttk.Label(tab, text="Название отчёта (подпапка сохранения):").pack(anchor=tk.W)
        name_entry = ttk.Entry(tab, width=45)
        name_entry.insert(0, name)
        name_entry.pack(anchor=tk.W, pady=(3, 8))
        attach_context_menu(name_entry)

        ttk.Label(tab, text="Интервал отправки отчёта (минуты между строками):").pack(anchor=tk.W)
        interval_entry = ttk.Entry(tab, width=15)
        interval_entry.insert(0, interval)
        interval_entry.pack(anchor=tk.W, pady=(3, 8))
        attach_context_menu(interval_entry)

        ttk.Label(tab, text="Текст отчёта (каждая строка — отдельный доклад с выбранным интервалом):\nВНИМАНИЕ! ТУТ ОБЯЗАТЕЛЬНО ДОЛЖНА БЫТЬ КОМАНДА, В ИНОМ СЛУЧАЕ КРАШ").pack(anchor=tk.W)
        text_area = tk.Text(tab, height=10, width=75)
        text_area.insert("1.0", "\n".join(lines))
        text_area.pack(fill=tk.BOTH, expand=True, pady=(3, 10))
        attach_context_menu(text_area)

        ctrl_frame = ttk.Frame(tab)
        ctrl_frame.pack(fill=tk.X)

        btn_start = ttk.Button(ctrl_frame, text="▶ Начать бинд", command=lambda r_id=report_id: self.engine.start_report_loop(r_id))
        btn_start.pack(side=tk.LEFT, padx=5)

        btn_stop = ttk.Button(ctrl_frame, text="⏹ Конец бинда", command=lambda r_id=report_id: self.engine.stop_report_loop(r_id))
        btn_stop.pack(side=tk.LEFT, padx=5)

        btn_del = ttk.Button(ctrl_frame, text="Удалить отчёт", command=lambda r_id=report_id: self.delete_report_tab(r_id))
        btn_del.pack(side=tk.RIGHT, padx=5)

        self.report_tabs_map[report_id] = {
            "tab": tab,
            "name": name_entry,
            "interval": interval_entry,
            "text": text_area
        }

    def add_new_report_tab(self):
        new_id = f"report_{uuid.uuid4().hex[:6]}"
        default_lines = [
            "/r [Доклад]"
        ]
        self.add_report_tab(new_id, "Патруль_КПП", "10", default_lines)

    def delete_report_tab(self, report_id: str):
        if report_id in self.report_tabs_map:
            self.engine.stop_report_loop(report_id)
            tab = self.report_tabs_map[report_id]["tab"]
            self.reports_notebook.forget(tab)
            del self.report_tabs_map[report_id]

    # --- Загрузка и Сохранение ---

    def load_all_from_config(self):
        self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, self.engine.config.get("screenshot_dir", "raports"))

        for b in self.engine.config.get("binds", []):
            self.add_bind_tab(
                b.get("id", f"bind_{uuid.uuid4().hex[:6]}"),
                b.get("title", "Бинд"),
                b.get("hotkey", ""),
                b.get("delay", "0.7"),
                b.get("lines", [])
            )

        for r in self.engine.config.get("reports", []):
            self.add_report_tab(
                r.get("id", f"report_{uuid.uuid4().hex[:6]}"),
                r.get("name", "Отчёт"),
                r.get("interval", "10"),
                r.get("lines", [])
            )

    def save_all(self):
        self.engine.config["screenshot_dir"] = self.dir_entry.get().strip() or "raports"

        binds_data = []
        for b_id, fields in self.bind_tabs_map.items():
            raw_text = fields["text"].get("1.0", tk.END).strip()
            lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
            binds_data.append({
                "id": b_id,
                "title": self.binds_notebook.tab(fields["tab"], "text"),
                "hotkey": fields["hk_btn"].get_hotkey(),
                "delay": fields["delay"].get().strip(),
                "lines": lines
            })

        reports_data = []
        for r_id, fields in self.report_tabs_map.items():
            name = fields["name"].get().strip()
            self.reports_notebook.tab(fields["tab"], text=name if name else "Отчёт")
            raw_text = fields["text"].get("1.0", tk.END).strip()
            lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
            reports_data.append({
                "id": r_id,
                "name": name,
                "interval": fields["interval"].get().strip(),
                "lines": lines
            })

        self.engine.config["binds"] = binds_data
        self.engine.config["reports"] = reports_data
        self.engine.save_config()
        messagebox.showinfo("Успех", "Настройки сохранены!")