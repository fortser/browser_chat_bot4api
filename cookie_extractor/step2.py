#!/usr/bin/env python3
"""
Firefox Cookie Exporter
Экспорт cookie из Firefox в JSON с графическим интерфейсом.
Выходной формат совместим с Playwright/Puppeteer.
"""

import sqlite3
import json
import shutil
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional
import threading


class FirefoxCookieExporter:
    """Класс для экспорта cookie из Firefox."""
    
    # Маппинг sameSite из Firefox в целевой формат
    SAMESITE_MAP = {
        0: "None",      # no_restriction -> None
        1: "Lax",       # lax -> Lax
        2: "Strict"     # strict -> Strict
    }
    
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.cookies: list[dict] = []
        self.stats = {
            'total': 0,
            'domains': 0
        }
    
    def reset(self):
        """Сброс состояния."""
        self.errors.clear()
        self.warnings.clear()
        self.cookies.clear()
        self.stats = {'total': 0, 'domains': 0}
    
    def extract_cookies(self, db_path: str) -> bool:
        """Извлечение cookie из базы данных Firefox."""
        self.reset()
        
        if not os.path.exists(db_path):
            self.errors.append(f"Файл не найден: {db_path}")
            return False
        
        temp_db = None
        try:
            temp_db = self._create_temp_copy(db_path)
            if not temp_db:
                return False
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Проверяем структуру таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='moz_cookies'")
            if not cursor.fetchone():
                self.errors.append("Таблица moz_cookies не найдена. Это не база cookie Firefox?")
                conn.close()
                return False
            
            # Читаем cookie
            cursor.execute("""
                SELECT host, name, value, path, expiry, isSecure, isHttpOnly, sameSite
                FROM moz_cookies
            """)
            
            domains_set = set()
            
            for row in cursor.fetchall():
                cookie = self._parse_row(row)
                if cookie:
                    self.cookies.append(cookie)
                    domains_set.add(self._extract_base_domain(cookie['domain']))
            
            conn.close()
            
            self.stats['total'] = len(self.cookies)
            self.stats['domains'] = len(domains_set)
            
            return True
            
        except sqlite3.DatabaseError as e:
            self.errors.append(f"Ошибка базы данных: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Неожиданная ошибка: {e}")
            return False
        finally:
            if temp_db and os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except:
                    pass
    
    def _create_temp_copy(self, db_path: str) -> Optional[str]:
        """Создание временной копии базы данных."""
        temp_dir = Path(os.environ.get('TEMP', os.environ.get('TMP', '.')))
        temp_db = temp_dir / f"temp_cookies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
        
        try:
            shutil.copy(db_path, temp_db)
            return str(temp_db)
        except PermissionError:
            self.errors.append("Нет доступа к файлу. Возможно, Firefox запущен. Закройте браузер и попробуйте снова.")
            return None
        except Exception as e:
            self.errors.append(f"Ошибка копирования файла: {e}")
            return None
    
    def _parse_row(self, row: tuple) -> Optional[dict]:
        """
        Парсинг строки из базы данных.
        
        Выходной формат (совместимый с Playwright/Puppeteer):
        {
            "name": "cookie_name",
            "value": "cookie_value",
            "domain": ".example.com",
            "path": "/",
            "expires": 1772438389.571332,
            "httpOnly": true,
            "secure": false,
            "sameSite": "Lax"
        }
        """
        try:
            host, name, value, path, expiry, is_secure, is_http_only, same_site = row
            
            # Конвертация expiry в float, -1 для сессионных cookie
            if expiry and expiry > 0:
                expires = float(expiry)
            else:
                expires = -1.0
            
            # Формируем cookie в целевом формате
            # Порядок полей: name -> value -> domain -> path -> expires -> httpOnly -> secure -> sameSite
            cookie = {
                "name": str(name) if name else "",
                "value": str(value) if value else "",
                "domain": str(host) if host else "",
                "path": str(path) if path else "/",
                "expires": expires,
                "httpOnly": bool(is_http_only),
                "secure": bool(is_secure),
                "sameSite": self.SAMESITE_MAP.get(same_site, "Lax")
            }
            
            return cookie
            
        except Exception as e:
            self.warnings.append(f"Ошибка парсинга cookie: {e}")
            return None
    
    def _extract_base_domain(self, domain: str) -> str:
        """Извлечение базового домена для группировки."""
        domain = domain.lstrip('.')
        parts = domain.split('.')
        
        if len(parts) > 2:
            # Обработка доменов типа .co.uk, .com.ru
            if len(parts[-2]) <= 3:
                return '.'.join(parts[-3:]) if len(parts) >= 3 else domain
            return '.'.join(parts[-2:])
        
        return domain
    
    def get_cookies_by_domain(self) -> dict[str, list[dict]]:
        """Группировка cookie по доменам."""
        grouped = defaultdict(list)
        for cookie in self.cookies:
            domain = self._extract_base_domain(cookie['domain'])
            grouped[domain].append(cookie)
        return dict(grouped)
    
    def _save_json(self, data: list[dict], filepath: str) -> bool:
        """Сохранение данных в JSON с правильным форматированием."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.errors.append(f"Ошибка сохранения {filepath}: {e}")
            return False
    
    def save_all_cookies(self, filepath: str) -> bool:
        """Сохранение всех cookie в один файл."""
        return self._save_json(self.cookies, filepath)
    
    def save_by_domain(self, output_dir: str, domains: Optional[list[str]] = None) -> int:
        """Сохранение cookie по отдельным файлам для каждого домена."""
        grouped = self.get_cookies_by_domain()
        
        if domains:
            grouped = {k: v for k, v in grouped.items() if k in domains}
        
        saved_count = 0
        
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            self.errors.append(f"Ошибка создания папки: {e}")
            return 0
        
        for domain, cookies in grouped.items():
            # Безопасное имя файла
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', domain)
            filepath = os.path.join(output_dir, f"{safe_name}.json")
            
            if self._save_json(cookies, filepath):
                saved_count += 1
            else:
                self.warnings.append(f"Не удалось сохранить {domain}")
        
        return saved_count


class CookieExporterGUI:
    """Графический интерфейс для Firefox Cookie Exporter."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Firefox Cookie Exporter")
        self.root.geometry("750x620")
        self.root.minsize(650, 520)
        
        self.exporter = FirefoxCookieExporter()
        self.db_path: Optional[str] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Создание интерфейса."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # === Выбор файла базы данных ===
        db_frame = ttk.LabelFrame(main_frame, text="База данных Firefox", padding="5")
        db_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        db_frame.columnconfigure(1, weight=1)
        
        ttk.Label(db_frame, text="cookies.sqlite:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.db_entry = ttk.Entry(db_frame)
        self.db_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(db_frame, text="Обзор...", command=self._browse_db).grid(row=0, column=2)
        
        # Подсказка
        hint_text = "Путь: %APPDATA%\\Mozilla\\Firefox\\Profiles\\[профиль]\\cookies.sqlite"
        ttk.Label(db_frame, text=hint_text, foreground="gray").grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))
        
        # Кнопка поиска профилей
        ttk.Button(db_frame, text="Найти профили Firefox", command=self._find_profiles).grid(row=2, column=0, columnspan=3, pady=(5, 0))
        
        # === Кнопка загрузки ===
        load_frame = ttk.Frame(main_frame)
        load_frame.grid(row=1, column=0, columnspan=3, pady=10)
        
        self.load_btn = ttk.Button(load_frame, text="Загрузить cookie", command=self._load_cookies)
        self.load_btn.pack()
        
        # === Статистика ===
        stats_frame = ttk.LabelFrame(main_frame, text="Статистика", padding="5")
        stats_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        self.stats_label = ttk.Label(stats_frame, text="Загрузите базу данных для просмотра статистики")
        self.stats_label.pack(anchor="w")
        
        # === Список доменов ===
        domains_frame = ttk.LabelFrame(main_frame, text="Найденные домены", padding="5")
        domains_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
        main_frame.rowconfigure(3, weight=1)
        domains_frame.columnconfigure(0, weight=1)
        domains_frame.rowconfigure(0, weight=1)
        
        columns = ('domain', 'count')
        self.domains_tree = ttk.Treeview(domains_frame, columns=columns, show='headings', selectmode='extended')
        self.domains_tree.heading('domain', text='Домен')
        self.domains_tree.heading('count', text='Cookie')
        self.domains_tree.column('domain', width=450)
        self.domains_tree.column('count', width=80, anchor='center')
        
        scrollbar = ttk.Scrollbar(domains_frame, orient="vertical", command=self.domains_tree.yview)
        self.domains_tree.configure(yscrollcommand=scrollbar.set)
        
        self.domains_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Кнопки выбора
        select_frame = ttk.Frame(domains_frame)
        select_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
        ttk.Button(select_frame, text="Выбрать все", command=self._select_all).pack(side="left", padx=2)
        ttk.Button(select_frame, text="Снять выбор", command=self._deselect_all).pack(side="left", padx=2)
        
        # Поле поиска
        search_frame = ttk.Frame(domains_frame)
        search_frame.grid(row=2, column=0, columnspan=2, pady=(5, 0), sticky="ew")
        ttk.Label(search_frame, text="Поиск:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        
        # === Опции экспорта ===
        export_frame = ttk.LabelFrame(main_frame, text="Экспорт", padding="5")
        export_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        # Чекбоксы
        self.export_all_var = tk.BooleanVar(value=True)
        self.export_split_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(export_frame, text="Сохранить все cookie в один файл", 
                        variable=self.export_all_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(export_frame, text="Сохранить отдельные файлы по доменам (в папку с датой/временем)", 
                        variable=self.export_split_var).grid(row=1, column=0, sticky="w")
        
        # Информация о формате
        format_info = "Формат: name → value → domain → path → expires (float) → httpOnly → secure → sameSite (Lax/Strict/None)"
        ttk.Label(export_frame, text=format_info, foreground="gray", font=('TkDefaultFont', 8)).grid(
            row=2, column=0, sticky="w", pady=(5, 0))
        
        # Кнопки экспорта
        export_btn_frame = ttk.Frame(export_frame)
        export_btn_frame.grid(row=3, column=0, pady=(10, 0))
        
        self.export_all_btn = ttk.Button(export_btn_frame, text="Экспортировать все", 
                                          command=self._export_all, state="disabled")
        self.export_all_btn.pack(side="left", padx=5)
        
        self.export_selected_btn = ttk.Button(export_btn_frame, text="Экспортировать выбранные", 
                                               command=self._export_selected, state="disabled")
        self.export_selected_btn.pack(side="left", padx=5)
        
        # === Лог ===
        log_frame = ttk.LabelFrame(main_frame, text="Лог", padding="5")
        log_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
        log_frame.columnconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=5, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="ew")
        self.log_text.config(state="disabled")
    
    def _browse_db(self):
        """Выбор файла базы данных."""
        initial_dir = self._get_firefox_profiles_dir()
        
        filepath = filedialog.askopenfilename(
            title="Выберите cookies.sqlite",
            initialdir=initial_dir,
            filetypes=[
                ("SQLite базы данных", "*.sqlite"),
                ("Все файлы", "*.*")
            ]
        )
        if filepath:
            self.db_path = filepath
            self.db_entry.delete(0, tk.END)
            self.db_entry.insert(0, filepath)
    
    def _get_firefox_profiles_dir(self) -> str:
        """Получение пути к профилям Firefox."""
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA', '')
            profiles_dir = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
            if os.path.exists(profiles_dir):
                return profiles_dir
        else:  # Linux/Mac
            home = os.path.expanduser('~')
            for path in ['.mozilla/firefox', 'Library/Application Support/Firefox/Profiles']:
                profiles_dir = os.path.join(home, path)
                if os.path.exists(profiles_dir):
                    return profiles_dir
        return os.path.expanduser('~')
    
    def _find_profiles(self):
        """Поиск профилей Firefox."""
        profiles_dir = self._get_firefox_profiles_dir()
        
        if not os.path.exists(profiles_dir):
            messagebox.showinfo("Информация", "Папка профилей Firefox не найдена")
            return
        
        found = []
        try:
            for item in os.listdir(profiles_dir):
                profile_path = os.path.join(profiles_dir, item)
                cookies_path = os.path.join(profile_path, 'cookies.sqlite')
                if os.path.isdir(profile_path) and os.path.exists(cookies_path):
                    # Получаем размер и дату модификации
                    stat = os.stat(cookies_path)
                    size_kb = stat.st_size / 1024
                    mod_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    found.append((item, cookies_path, size_kb, mod_time))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка поиска профилей: {e}")
            return
        
        if not found:
            messagebox.showinfo("Информация", "Профили Firefox с cookies.sqlite не найдены")
            return
        
        self._show_profile_selector(found)
    
    def _show_profile_selector(self, profiles: list[tuple]):
        """Диалог выбора профиля."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Выберите профиль Firefox")
        dialog.geometry("600x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Найденные профили:").pack(pady=(10, 5))
        
        # Treeview для отображения профилей
        columns = ('profile', 'size', 'modified')
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=10)
        tree.heading('profile', text='Профиль')
        tree.heading('size', text='Размер')
        tree.heading('modified', text='Изменён')
        tree.column('profile', width=300)
        tree.column('size', width=100, anchor='center')
        tree.column('modified', width=150, anchor='center')
        
        for name, path, size, mod_time in profiles:
            tree.insert('', 'end', values=(name, f"{size:.1f} KB", mod_time), tags=(path,))
        
        tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        def on_select():
            selection = tree.selection()
            if selection:
                item = selection[0]
                path = tree.item(item, 'tags')[0]
                self.db_path = path
                self.db_entry.delete(0, tk.END)
                self.db_entry.insert(0, path)
                dialog.destroy()
        
        def on_double_click(event):
            on_select()
        
        tree.bind('<Double-1>', on_double_click)
        ttk.Button(dialog, text="Выбрать", command=on_select).pack(pady=10)
    
    def _log(self, message: str, level: str = "info"):
        """Добавление сообщения в лог."""
        self.log_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"info": "ℹ", "success": "✓", "error": "✗", "warning": "⚠"}.get(level, "•")
        self.log_text.insert(tk.END, f"[{timestamp}] {prefix} {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
    
    def _clear_log(self):
        """Очистка лога."""
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
    
    def _load_cookies(self):
        """Загрузка cookie из базы данных."""
        self.db_path = self.db_entry.get().strip()
        
        if not self.db_path:
            messagebox.showerror("Ошибка", "Выберите файл cookies.sqlite")
            return
        
        self._clear_log()
        self._log(f"Загрузка: {Path(self.db_path).name}")
        
        self.load_btn.config(state="disabled")
        
        def load_thread():
            success = self.exporter.extract_cookies(self.db_path)
            self.root.after(0, lambda: self._on_load_complete(success))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _on_load_complete(self, success: bool):
        """Обработка завершения загрузки."""
        self.load_btn.config(state="normal")
        
        for error in self.exporter.errors:
            self._log(error, "error")
        for warning in self.exporter.warnings:
            self._log(warning, "warning")
        
        if not success:
            self.stats_label.config(text="Ошибка загрузки. Проверьте лог.")
            self.export_all_btn.config(state="disabled")
            self.export_selected_btn.config(state="disabled")
            return
        
        stats = self.exporter.stats
        self.stats_label.config(text=f"Всего cookie: {stats['total']} | Уникальных доменов: {stats['domains']}")
        
        self._populate_domains_tree()
        
        self._log(f"Загружено {stats['total']} cookie из {stats['domains']} доменов", "success")
        
        self.export_all_btn.config(state="normal")
        self.export_selected_btn.config(state="normal")
    
    def _populate_domains_tree(self, filter_text: str = ""):
        """Заполнение списка доменов."""
        self.domains_tree.delete(*self.domains_tree.get_children())
        grouped = self.exporter.get_cookies_by_domain()
        
        filter_text = filter_text.lower()
        
        for domain in sorted(grouped.keys()):
            if filter_text and filter_text not in domain.lower():
                continue
            count = len(grouped[domain])
            self.domains_tree.insert('', 'end', values=(domain, count))
    
    def _on_search(self, *args):
        """Обработка поиска."""
        filter_text = self.search_var.get()
        self._populate_domains_tree(filter_text)
    
    def _select_all(self):
        """Выбрать все домены."""
        for item in self.domains_tree.get_children():
            self.domains_tree.selection_add(item)
    
    def _deselect_all(self):
        """Снять выбор."""
        self.domains_tree.selection_remove(*self.domains_tree.get_children())
    
    def _get_selected_domains(self) -> list[str]:
        """Получение выбранных доменов."""
        selected = []
        for item in self.domains_tree.selection():
            values = self.domains_tree.item(item, 'values')
            if values:
                selected.append(values[0])
        return selected
    
    def _generate_output_dir_name(self) -> str:
        """Генерация имени папки с датой/временем."""
        db_name = Path(self.db_path).stem if self.db_path else "cookies"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{db_name}_{timestamp}"
    
    def _export_all(self):
        """Экспорт всех cookie."""
        self._do_export(None)
    
    def _export_selected(self):
        """Экспорт выбранных доменов."""
        selected = self._get_selected_domains()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите домены для экспорта")
            return
        self._do_export(selected)
    
    def _do_export(self, domains: Optional[list[str]]):
        """Выполнение экспорта."""
        export_all = self.export_all_var.get()
        export_split = self.export_split_var.get()
        
        if not export_all and not export_split:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы один вариант экспорта")
            return
        
        output_base = filedialog.askdirectory(title="Выберите папку для сохранения")
        if not output_base:
            return
        
        saved_files = []
        total_cookies = 0
        
        # Экспорт в один файл
        if export_all:
            if domains:
                grouped = self.exporter.get_cookies_by_domain()
                filtered_cookies = []
                for d in domains:
                    if d in grouped:
                        filtered_cookies.extend(grouped[d])
                
                original_cookies = self.exporter.cookies
                self.exporter.cookies = filtered_cookies
                
                filename = f"cookies_selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join(output_base, filename)
                
                if self.exporter.save_all_cookies(filepath):
                    self._log(f"Сохранён: {filename} ({len(filtered_cookies)} cookie)", "success")
                    saved_files.append(filepath)
                    total_cookies += len(filtered_cookies)
                
                self.exporter.cookies = original_cookies
            else:
                filename = f"cookies_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join(output_base, filename)
                
                if self.exporter.save_all_cookies(filepath):
                    self._log(f"Сохранён: {filename} ({len(self.exporter.cookies)} cookie)", "success")
                    saved_files.append(filepath)
                    total_cookies += len(self.exporter.cookies)
        
        # Экспорт по доменам
        if export_split:
            dir_name = self._generate_output_dir_name()
            output_dir = os.path.join(output_base, dir_name)
            
            count = self.exporter.save_by_domain(output_dir, domains)
            
            if count > 0:
                self._log(f"Сохранено {count} файлов в папку: {dir_name}", "success")
                saved_files.append(output_dir)
            
            for warning in self.exporter.warnings:
                self._log(warning, "warning")
            self.exporter.warnings.clear()
        
        if saved_files:
            messagebox.showinfo("Готово", f"Экспорт завершён!\n\nСохранено в:\n{output_base}")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить файлы. Проверьте лог.")
    
    def run(self):
        """Запуск приложения."""
        self.root.mainloop()


def main():
    app = CookieExporterGUI()
    app.run()


if __name__ == "__main__":
    main()
