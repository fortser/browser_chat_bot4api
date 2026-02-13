#!/usr/bin/env python3
"""
Visual Director Response Parser v2.2 GUI
Надёжный парсер с графическим интерфейсом (Tkinter)
С улучшенным логированием ошибок и поддержкой альтернативных полей

Установка зависимостей:
    pip install json-repair pydantic

Запуск:
    python vd_parser_gui.py
"""

import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from collections import Counter
import threading

# Внешние зависимости
try:
    from json_repair import repair_json
except ImportError:
    repair_json = None

try:
    from pydantic import BaseModel, Field, field_validator, ValidationError, model_validator
except ImportError:
    BaseModel = None


# ============================================================================
# CONFIGURATION - НАСТРОЙКА ПОЛЕЙ
# ============================================================================

# Альтернативные имена полей (первое — каноническое, остальные — алиасы)
FIELD_ALIASES = {
    "reasoning": ["reasoning", "art_preservation", "analysis", "thought_process", "explanation"],
    "optimized_prompt": ["optimized_prompt", "prompt", "result", "output", "final_prompt"]
}


def normalize_field_names(data: dict) -> dict:
    """Приводит альтернативные имена полей к каноническим."""
    normalized = {}
    used_keys = set()
    
    for canonical_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in data and alias not in used_keys:
                normalized[canonical_name] = data[alias]
                used_keys.add(alias)
                break
    
    # Копируем остальные поля как есть
    for key, value in data.items():
        if key not in used_keys and key not in normalized:
            normalized[key] = value
    
    return normalized


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

if BaseModel:
    class OptimizedResponse(BaseModel):
        """Схема ответа Visual Director с поддержкой альтернативных полей."""
        
        reasoning: str = Field(..., min_length=5)
        optimized_prompt: str = Field(..., min_length=20)
        
        @model_validator(mode='before')
        @classmethod
        def normalize_fields(cls, values):
            """Нормализует альтернативные имена полей перед валидацией."""
            if isinstance(values, dict):
                return normalize_field_names(values)
            return values
        
        @field_validator('optimized_prompt')
        @classmethod
        def clean_prompt(cls, v: str) -> str:
            cleaned = v.replace('\n', ' ').replace('\r', '').strip()
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            return cleaned
        
        @field_validator('reasoning')
        @classmethod
        def clean_reasoning(cls, v: str) -> str:
            return v.strip()

    class TaskResult(BaseModel):
        """Схема одной задачи."""
        
        task_id: str = ""
        task_name: str = ""
        prompt: str = ""
        response: str = ""
        status: str = "completed"
        started_at: Optional[str] = None
        completed_at: Optional[str] = None
        error_message: Optional[str] = None
        duration_seconds: Optional[float] = None
        
        model_config = {"extra": "ignore"}

    class SessionData(BaseModel):
        """Схема сессии."""
        
        session_id: str = ""
        sequence_name: Optional[str] = None
        started_at: Optional[str] = None
        completed_at: Optional[str] = None
        results: list[TaskResult] = []
        total_tasks: int = 0
        completed_tasks: int = 0
        failed_tasks: int = 0
        
        model_config = {"extra": "ignore"}
        
        @field_validator('results', mode='before')
        @classmethod
        def ensure_list(cls, v):
            if v is None:
                return []
            if isinstance(v, dict):
                return [v]
            return v


# ============================================================================
# ERROR DIAGNOSTICS
# ============================================================================

@dataclass
class DetailedError:
    """Детальная информация об ошибке."""
    task_index: int
    task_id: str
    task_name: str
    error_type: str
    error_message: str
    response_preview: str
    response_length: int
    suggestions: list[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


ERROR_TYPE_DESCRIPTIONS = {
    "empty_response": "Пустой ответ от модели — возможно таймаут или ошибка API",
    "json_parse": "Модель вернула текст вместо JSON — проверьте системный промпт",
    "missing_field": "Отсутствуют обязательные поля — модель не следует формату",
    "validation": "Данные не прошли валидацию — некорректные значения полей",
    "unknown": "Неизвестная ошибка"
}


# ============================================================================
# PARSING ENGINE
# ============================================================================

@dataclass
class ParseResult:
    """Результат парсинга одного response."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    error_type: str = "unknown"
    repair_applied: bool = False
    field_mapping: Optional[dict] = None  # Какие поля были преобразованы


@dataclass
class ParsingStats:
    """Статистика парсинга."""
    total_tasks: int = 0
    processed_tasks: int = 0
    skipped_tasks: int = 0
    successful_parses: int = 0
    failed_parses: int = 0
    repairs_applied: int = 0
    fields_normalized: int = 0  # Сколько раз применялась нормализация полей
    errors: list[str] = field(default_factory=list)
    error_types: dict = field(default_factory=dict)


class RobustJsonParser:
    """Трёхуровневый парсер JSON с восстановлением ошибок и детальной диагностикой."""
    
    def __init__(self, skip_first: bool = True):
        self.skip_first = skip_first
        self.stats = ParsingStats()
        self.detailed_errors: list[DetailedError] = []
    
    def _preprocess(self, raw_text: str) -> str:
        """Базовая предобработка текста."""
        text = raw_text.strip()
        text = text.strip('\ufeff\u200b\u200c\u200d')
        
        if text.startswith('```'):
            lines = text.split('\n')
            start_idx = 1 if lines[0].strip().startswith('```') else 0
            end_idx = -1 if lines[-1].strip() == '```' else len(lines)
            text = '\n'.join(lines[start_idx:end_idx])
        
        return text.strip()
    
    def _suggest_json_fixes(self, response: str) -> list[str]:
        """Анализирует response и предлагает исправления."""
        suggestions = []
        
        if not response:
            suggestions.append("Response пустой — проверьте работу API")
            return suggestions
        
        stripped = response.strip()
        
        if not stripped.startswith('{') and not stripped.startswith('['):
            suggestions.append("Response не начинается с '{' или '[' — модель вернула текст вместо JSON")
            if '{' in response:
                json_start = response.find('{')
                suggestions.append(f"JSON возможно начинается с позиции {json_start}")
        
        if '```' in response:
            suggestions.append("Обнаружены markdown code blocks (```) — модель обернула JSON в код")
        
        # Проверяем наличие любого из известных полей
        known_fields = set()
        for aliases in FIELD_ALIASES.values():
            known_fields.update(aliases)
        
        found_fields = [f for f in known_fields if f'"{f}"' in response or f"'{f}'" in response]
        if not found_fields:
            suggestions.append(f"Не найдено ни одного известного поля. Известные поля: {list(known_fields)}")
        
        open_braces = response.count('{')
        close_braces = response.count('}')
        if open_braces != close_braces:
            suggestions.append(f"Несбалансированные скобки: '{{' = {open_braces}, '}}' = {close_braces}")
        
        if not stripped.endswith('}') and not stripped.endswith(']'):
            suggestions.append("Response не заканчивается на '}' или ']' — возможно ответ обрезан")
        
        if 'I\'ll' in response or 'I will' in response or 'Here' in response:
            suggestions.append("Модель начала с вводного текста — усильте инструкцию 'respond ONLY with JSON'")
        
        if not suggestions:
            suggestions.append("Попробуйте проверить response в JSON-валидаторе (jsonlint.com)")
        
        return suggestions
    
    def _create_detailed_error(
        self, 
        task_info: dict, 
        error_type: str, 
        message: str, 
        response: str,
        suggestions: list[str] = None
    ) -> DetailedError:
        """Создаёт детальное описание ошибки."""
        if suggestions is None:
            suggestions = self._suggest_json_fixes(response)
        
        return DetailedError(
            task_index=task_info.get("index", -1),
            task_id=task_info.get("task_id", "unknown"),
            task_name=task_info.get("task_name", "unnamed"),
            error_type=error_type,
            error_message=message,
            response_preview=response[:500] if response else "",
            response_length=len(response) if response else 0,
            suggestions=suggestions
        )
    
    def _detect_field_mapping(self, original_data: dict, normalized_data: dict) -> dict:
        """Определяет какие поля были преобразованы."""
        mapping = {}
        for canonical_name, aliases in FIELD_ALIASES.items():
            if canonical_name in normalized_data:
                for alias in aliases:
                    if alias in original_data and alias != canonical_name:
                        mapping[alias] = canonical_name
                        break
        return mapping
    
    def parse_raw_json(self, raw_text: str) -> tuple[dict, bool]:
        """Парсит JSON с автовосстановлением."""
        text = self._preprocess(raw_text)
        
        # Level 1: Прямой парсинг
        try:
            return json.loads(text), False
        except json.JSONDecodeError:
            pass
        
        # Level 2: json-repair
        if repair_json:
            try:
                repaired = repair_json(text, return_objects=True)
                if isinstance(repaired, dict):
                    return repaired, True
            except Exception:
                pass
            
            # Level 3: Агрессивное восстановление
            try:
                text_fixed = re.sub(r',(\s*[\]\}])', r'\1', text)
                text_fixed = re.sub(r'(?<=[{,\s])(\w+)(?=\s*:)', r'"\1"', text_fixed)
                repaired = repair_json(text_fixed, return_objects=True)
                if isinstance(repaired, dict):
                    return repaired, True
            except Exception:
                pass
        
        raise ValueError("Cannot parse JSON after all recovery attempts")
    
    def parse_optimized_response(self, response_str: str, task_info: dict = None) -> ParseResult:
        """Парсит вложенный response с детальной диагностикой."""
        task_info = task_info or {}
        
        # Проверка на пустой response
        if not response_str or not response_str.strip():
            error = self._create_detailed_error(
                task_info,
                error_type="empty_response",
                message="Response is empty or whitespace-only",
                response=response_str,
                suggestions=[
                    "Проверьте, что генеративная модель вернула ответ",
                    "Возможно, произошёл таймаут или ошибка API",
                    "Проверьте лимиты токенов и rate limits"
                ]
            )
            self.detailed_errors.append(error)
            return ParseResult(
                success=False, 
                error="Empty response", 
                error_type="empty_response"
            )
        
        # Попытка парсинга JSON
        try:
            data, repair_applied = self.parse_raw_json(response_str)
        except ValueError as e:
            error = self._create_detailed_error(
                task_info,
                error_type="json_parse",
                message=str(e),
                response=response_str
            )
            self.detailed_errors.append(error)
            return ParseResult(
                success=False, 
                error=f"JSON parse failed: {e}", 
                error_type="json_parse"
            )
        
        # Сохраняем оригинальные данные для отслеживания маппинга
        original_data = data.copy()
        
        # Нормализация полей (без Pydantic)
        if not BaseModel:
            data = normalize_field_names(data)
        
        # Определяем какие поля были преобразованы
        field_mapping = self._detect_field_mapping(original_data, data if not BaseModel else normalize_field_names(original_data))
        
        if field_mapping:
            self.stats.fields_normalized += 1
        
        # Валидация через Pydantic (если доступен)
        if BaseModel:
            try:
                validated = OptimizedResponse(**original_data)  # Pydantic сам нормализует
                data = {
                    "reasoning": validated.reasoning,
                    "optimized_prompt": validated.optimized_prompt
                }
            except ValidationError as e:
                # Формируем понятное сообщение об ошибке
                error_details = []
                for err in e.errors():
                    loc = err.get('loc', ['unknown'])
                    msg = err.get('msg', 'unknown error')
                    error_details.append(f"{'.'.join(map(str, loc))}: {msg}")
                
                error_message = "; ".join(error_details)
                
                # Определяем тип ошибки
                if any('missing' in str(err.get('type', '')) for err in e.errors()):
                    error_type = "missing_field"
                else:
                    error_type = "validation"
                
                # Формируем рекомендации
                suggestions = [
                    f"Полученные поля в оригинале: {list(original_data.keys())}",
                    f"Известные алиасы для 'reasoning': {FIELD_ALIASES['reasoning']}",
                    f"Известные алиасы для 'optimized_prompt': {FIELD_ALIASES['optimized_prompt']}"
                ]
                
                if error_type == "missing_field":
                    suggestions.insert(0, "Добавьте недостающее поле в системный промпт или расширьте FIELD_ALIASES в парсере")
                
                error = self._create_detailed_error(
                    task_info,
                    error_type=error_type,
                    message=error_message,
                    response=response_str,
                    suggestions=suggestions
                )
                self.detailed_errors.append(error)
                return ParseResult(
                    success=False, 
                    error=error_message, 
                    error_type=error_type
                )
        else:
            # Проверка обязательных полей без Pydantic
            missing_fields = []
            if "optimized_prompt" not in data:
                missing_fields.append("optimized_prompt")
            if "reasoning" not in data:
                missing_fields.append("reasoning")
            
            if missing_fields:
                error = self._create_detailed_error(
                    task_info,
                    error_type="missing_field",
                    message=f"Missing required fields: {missing_fields}",
                    response=response_str,
                    suggestions=[
                        f"Полученные поля: {list(original_data.keys())}",
                        f"Известные алиасы для 'reasoning': {FIELD_ALIASES['reasoning']}",
                        f"Известные алиасы для 'optimized_prompt': {FIELD_ALIASES['optimized_prompt']}",
                        "Добавьте недостающее поле в FIELD_ALIASES или измените системный промпт"
                    ]
                )
                self.detailed_errors.append(error)
                return ParseResult(
                    success=False, 
                    error=f"Missing fields: {missing_fields}", 
                    error_type="missing_field"
                )
            
            # Минимальная валидация
            prompt = data.get("optimized_prompt", "")
            if len(prompt) < 20:
                error = self._create_detailed_error(
                    task_info,
                    error_type="validation",
                    message=f"optimized_prompt too short ({len(prompt)} chars, min 20)",
                    response=response_str,
                    suggestions=[
                        f"Промпт содержит только {len(prompt)} символов (минимум 20)",
                        "Возможно модель не поняла задачу оптимизации"
                    ]
                )
                self.detailed_errors.append(error)
                return ParseResult(
                    success=False, 
                    error=f"Prompt too short ({len(prompt)} chars)", 
                    error_type="validation"
                )
            
            # Очистка
            data["optimized_prompt"] = re.sub(r'\s{2,}', ' ', prompt.replace('\n', ' ').strip())
            data["reasoning"] = data.get("reasoning", "").strip()
        
        return ParseResult(
            success=True, 
            data=data, 
            repair_applied=repair_applied,
            field_mapping=field_mapping
        )
    
    def parse_session_file(self, file_path: str) -> tuple[Optional[dict], ParsingStats]:
        """Парсит файл сессии."""
        self.stats = ParsingStats()
        self.detailed_errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except FileNotFoundError:
            self.stats.errors.append(f"File not found: {file_path}")
            return None, self.stats
        except PermissionError:
            self.stats.errors.append(f"Permission denied: {file_path}")
            return None, self.stats
        except Exception as e:
            self.stats.errors.append(f"Cannot read file: {e}")
            return None, self.stats
        
        try:
            data, outer_repair = self.parse_raw_json(raw_content)
            if outer_repair:
                self.stats.repairs_applied += 1
        except Exception as e:
            self.stats.errors.append(f"Cannot parse outer JSON structure: {e}")
            return None, self.stats
        
        if BaseModel:
            try:
                session = SessionData(**data)
                data = session.model_dump()
            except ValidationError as e:
                self.stats.errors.append(f"Session validation failed: {e}")
                return None, self.stats
        
        results = data.get("results", [])
        self.stats.total_tasks = len(results)
        
        return data, self.stats
    
    def process_session(self, data: dict) -> tuple[dict, list[str], ParsingStats]:
        """Обрабатывает сессию с детальным трекингом ошибок."""
        prompts = []
        results = data.get("results", [])
        
        technical_data = {
            "session_id": data.get("session_id", ""),
            "sequence_name": data.get("sequence_name"),
            "started_at": data.get("started_at"),
            "completed_at": data.get("completed_at"),
            "total_tasks": data.get("total_tasks", 0),
            "completed_tasks": data.get("completed_tasks", 0),
            "failed_tasks": data.get("failed_tasks", 0),
            "parsing_stats": {},
            "field_aliases_used": dict(FIELD_ALIASES),
            "tasks": []
        }
        
        error_type_counter = Counter()
        field_mappings_used = Counter()
        
        for idx, task in enumerate(results):
            task_id = task.get("task_id", f"task_{idx}")
            task_name = task.get("task_name", f"unnamed_{idx}")
            
            if self.skip_first and idx == 0:
                self.stats.skipped_tasks += 1
                technical_data["tasks"].append({
                    "task_id": task_id,
                    "task_name": task_name,
                    "status": "skipped",
                    "skip_reason": "First response (system prompt) - skipped by user setting"
                })
                continue
            
            self.stats.processed_tasks += 1
            
            response_str = task.get("response", "")
            
            task_info = {
                "index": idx,
                "task_id": task_id,
                "task_name": task_name
            }
            
            parse_result = self.parse_optimized_response(response_str, task_info)
            
            task_info_output = {
                "task_id": task_id,
                "task_name": task_name,
                "status": task.get("status", ""),
                "duration_seconds": task.get("duration_seconds"),
                "parse_success": parse_result.success,
                "repair_applied": parse_result.repair_applied,
            }
            
            if parse_result.field_mapping:
                task_info_output["field_mapping"] = parse_result.field_mapping
                for orig, canonical in parse_result.field_mapping.items():
                    field_mappings_used[f"{orig} → {canonical}"] += 1
            
            if parse_result.success and parse_result.data:
                self.stats.successful_parses += 1
                if parse_result.repair_applied:
                    self.stats.repairs_applied += 1
                
                task_info_output["reasoning"] = parse_result.data.get("reasoning", "")
                task_info_output["prompt_length"] = len(parse_result.data.get("optimized_prompt", ""))
                
                prompts.append(parse_result.data["optimized_prompt"])
            else:
                self.stats.failed_parses += 1
                task_info_output["parse_error"] = parse_result.error
                task_info_output["error_type"] = parse_result.error_type
                
                error_type_counter[parse_result.error_type] += 1
                self.stats.errors.append(f"Task {task_id}: [{parse_result.error_type}] {parse_result.error}")
            
            technical_data["tasks"].append(task_info_output)
        
        processed = self.stats.processed_tasks or 1
        self.stats.error_types = dict(error_type_counter)
        
        technical_data["parsing_stats"] = {
            "total_tasks": self.stats.total_tasks,
            "skipped_tasks": self.stats.skipped_tasks,
            "processed_tasks": self.stats.processed_tasks,
            "successful_parses": self.stats.successful_parses,
            "failed_parses": self.stats.failed_parses,
            "repairs_applied": self.stats.repairs_applied,
            "fields_normalized": self.stats.fields_normalized,
            "success_rate": f"{(self.stats.successful_parses / processed) * 100:.1f}%",
            "error_types": self.stats.error_types,
            "field_mappings_used": dict(field_mappings_used)
        }
        
        return technical_data, prompts, self.stats
    
    def get_error_summary(self) -> dict:
        """Возвращает сводку по ошибкам."""
        if not self.detailed_errors:
            return {"total_errors": 0}
        
        type_counter = Counter(e.error_type for e in self.detailed_errors)
        
        return {
            "total_errors": len(self.detailed_errors),
            "by_type": dict(type_counter),
            "most_common": type_counter.most_common(1)[0] if type_counter else None,
            "descriptions": {
                error_type: ERROR_TYPE_DESCRIPTIONS.get(error_type, "Unknown error")
                for error_type in type_counter.keys()
            }
        }


# ============================================================================
# GUI APPLICATION
# ============================================================================

class VDParserApp:
    """Графическое приложение для парсинга с улучшенным логированием."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Visual Director Parser v2.2")
        self.root.geometry("800x650")
        self.root.minsize(700, 550)
        
        self.input_files: list[str] = []
        self.output_dir: Optional[str] = None
        self.skip_first_var = tk.BooleanVar(value=True)
        self.verbose_var = tk.BooleanVar(value=True)
        
        self._setup_ui()
        self._check_dependencies()
    
    def _setup_ui(self):
        """Создаёт интерфейс."""
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== Секция выбора файлов =====
        files_frame = ttk.LabelFrame(main_frame, text="Входные файлы", padding="10")
        files_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.files_listbox = tk.Listbox(files_frame, height=4, selectmode=tk.EXTENDED)
        self.files_listbox.pack(fill=tk.X, pady=(0, 5))
        
        files_btn_frame = ttk.Frame(files_frame)
        files_btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            files_btn_frame, 
            text="📂 Добавить файлы...", 
            command=self._add_files
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            files_btn_frame, 
            text="🗑 Удалить выбранные", 
            command=self._remove_selected
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            files_btn_frame, 
            text="✖ Очистить", 
            command=self._clear_files
        ).pack(side=tk.LEFT)
        
        # ===== Секция папки вывода =====
        output_frame = ttk.LabelFrame(main_frame, text="Папка для результатов", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        output_inner = ttk.Frame(output_frame)
        output_inner.pack(fill=tk.X)
        
        self.output_label = ttk.Label(
            output_inner, 
            text="(рядом с исходными файлами)", 
            foreground="gray"
        )
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            output_inner, 
            text="📁 Выбрать...", 
            command=self._select_output
        ).pack(side=tk.RIGHT)
        
        # ===== Секция настроек =====
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        skip_check = ttk.Checkbutton(
            settings_frame,
            text="Пропустить первый ответ (системный запрос)",
            variable=self.skip_first_var
        )
        skip_check.pack(anchor=tk.W)
        
        verbose_check = ttk.Checkbutton(
            settings_frame,
            text="Подробный вывод ошибок в лог",
            variable=self.verbose_var
        )
        verbose_check.pack(anchor=tk.W)
        
        # Информация об алиасах полей
        aliases_text = f"📋 Известные алиасы полей: reasoning={FIELD_ALIASES['reasoning']}"
        hint_label = ttk.Label(
            settings_frame,
            text=aliases_text,
            foreground="gray",
            font=("TkDefaultFont", 8)
        )
        hint_label.pack(anchor=tk.W, pady=(5, 0))
        
        # ===== Кнопка запуска =====
        self.process_btn = ttk.Button(
            main_frame,
            text="▶ Обработать файлы",
            command=self._process_files,
            style="Accent.TButton"
        )
        self.process_btn.pack(fill=tk.X, pady=(0, 10), ipady=8)
        
        # ===== Лог =====
        log_frame = ttk.LabelFrame(main_frame, text="Лог выполнения", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=14,
            state=tk.DISABLED,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Теги для цветного вывода
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("dim", foreground="gray")
        self.log_text.tag_configure("header", foreground="purple", font=("Consolas", 9, "bold"))
        
        # ===== Статус-бар =====
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=(5, 2)
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _check_dependencies(self):
        """Проверяет зависимости."""
        missing = []
        if not repair_json:
            missing.append("json-repair")
        if not BaseModel:
            missing.append("pydantic")
        
        if missing:
            self._log(f"⚠️ Не установлены: {', '.join(missing)}", "warning")
            self._log("   Установите: pip install json-repair pydantic", "warning")
            self._log("   Парсер будет работать с ограничениями\n", "warning")
        else:
            self._log("✅ Все зависимости установлены", "success")
            self._log(f"📋 Поддерживаемые алиасы полей:", "info")
            for canonical, aliases in FIELD_ALIASES.items():
                self._log(f"   {canonical}: {aliases}", "dim")
            self._log("")
    
    def _log(self, message: str, tag: str = None):
        """Добавляет сообщение в лог."""
        self.log_text.config(state=tk.NORMAL)
        if tag:
            self.log_text.insert(tk.END, message + "\n", tag)
        else:
            self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def _clear_log(self):
        """Очищает лог."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _add_files(self):
        """Добавляет файлы через диалог."""
        files = filedialog.askopenfilenames(
            title="Выберите JSON-файлы",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
                self.files_listbox.insert(tk.END, Path(f).name)
        
        self._update_status()
    
    def _remove_selected(self):
        """Удаляет выбранные файлы."""
        selected = list(self.files_listbox.curselection())
        for idx in reversed(selected):
            self.files_listbox.delete(idx)
            del self.input_files[idx]
        
        self._update_status()
    
    def _clear_files(self):
        """Очищает список файлов."""
        self.files_listbox.delete(0, tk.END)
        self.input_files.clear()
        self._update_status()
    
    def _select_output(self):
        """Выбирает папку вывода."""
        folder = filedialog.askdirectory(title="Выберите папку для результатов")
        if folder:
            self.output_dir = folder
            self.output_label.config(text=folder, foreground="black")
    
    def _update_status(self):
        """Обновляет статус-бар."""
        count = len(self.input_files)
        if count == 0:
            self.status_var.set("Готов к работе")
        else:
            self.status_var.set(f"Выбрано файлов: {count}")
    
    def _process_files(self):
        """Запускает обработку файлов."""
        if not self.input_files:
            messagebox.showwarning("Внимание", "Добавьте файлы для обработки")
            return
        
        self.process_btn.config(state=tk.DISABLED)
        self._clear_log()
        
        thread = threading.Thread(target=self._process_worker, daemon=True)
        thread.start()
    
    def _process_worker(self):
        """Рабочий поток обработки."""
        skip_first = self.skip_first_var.get()
        verbose = self.verbose_var.get()
        
        self._log(f"🚀 Начинаю обработку {len(self.input_files)} файлов...", "header")
        self._log(f"   ⏭ Пропуск первого ответа: {'включён' if skip_first else 'выключён'}", "info")
        self._log(f"   📝 Подробные ошибки: {'включены' if verbose else 'выключены'}", "info")
        self._log("")
        
        total_prompts = 0
        total_errors = 0
        total_normalized = 0
        
        for file_path in self.input_files:
            file_name = Path(file_path).name
            self._log(f"📄 Обрабатываю: {file_name}", "header")
            
            parser = RobustJsonParser(skip_first=skip_first)
            
            data, stats = parser.parse_session_file(file_path)
            
            if data is None:
                self._log(f"   ❌ Ошибка чтения файла", "error")
                for err in stats.errors:
                    self._log(f"      {err}", "error")
                total_errors += 1
                self._log("")
                continue
            
            technical_data, prompts, stats = parser.process_session(data)
            
            # Выводим информацию о нормализации полей
            if stats.fields_normalized > 0:
                self._log(f"   🔄 Нормализовано полей: {stats.fields_normalized}", "info")
                # Выводим какие именно поля были преобразованы
                field_mappings = technical_data.get("parsing_stats", {}).get("field_mappings_used", {})
                for mapping, count in field_mappings.items():
                    self._log(f"      {mapping}: {count} раз", "dim")
            
            # Выводим ошибки в лог (если включён подробный режим)
            if verbose and parser.detailed_errors:
                self._log(f"   ─── Детали ошибок ───", "warning")
                for err in parser.detailed_errors[:5]:  # Показываем первые 5
                    self._log_detailed_error(err)
                if len(parser.detailed_errors) > 5:
                    self._log(f"   ... и ещё {len(parser.detailed_errors) - 5} ошибок (см. файл *_errors.json)", "dim")
            
            try:
                saved_files = self._save_outputs(
                    technical_data, prompts, file_path, parser
                )
                
                total_prompts += len(prompts)
                total_errors += stats.failed_parses
                total_normalized += stats.fields_normalized
                
                if stats.failed_parses == 0:
                    self._log(f"   ✅ Успешно!", "success")
                else:
                    self._log(f"   ⚠️ Частичный успех", "warning")
                
                self._log(f"      Задач: {stats.total_tasks} | "
                         f"Пропущено: {stats.skipped_tasks} | "
                         f"Успешно: {stats.successful_parses} | "
                         f"Ошибок: {stats.failed_parses}")
                
                if stats.repairs_applied > 0:
                    self._log(f"      🔧 JSON repairs: {stats.repairs_applied}", "info")
                
                if stats.error_types:
                    self._log(f"      📊 Типы ошибок:", "warning")
                    for error_type, count in stats.error_types.items():
                        desc = ERROR_TYPE_DESCRIPTIONS.get(error_type, "")
                        self._log(f"         • {error_type}: {count} — {desc}", "dim")
                
                self._log(f"      📁 Сохранено:")
                for saved_file in saved_files:
                    self._log(f"         → {saved_file.name}", "dim")
                
                self._log("")
                
            except Exception as e:
                self._log(f"   ❌ Ошибка сохранения: {e}", "error")
                total_errors += 1
                self._log("")
        
        # Итог
        self._log("═" * 60, "header")
        if total_errors == 0:
            self._log(f"🎉 УСПЕХ! Извлечено промптов: {total_prompts}", "success")
        else:
            self._log(f"📊 ИТОГО: промптов: {total_prompts} | ошибок: {total_errors}", 
                     "success" if total_errors == 0 else "warning")
        
        if total_normalized > 0:
            self._log(f"   🔄 Всего нормализовано полей: {total_normalized}", "info")
        
        if total_errors > 0:
            self._log(f"   💡 Проверьте файлы *_errors.json для диагностики", "info")
            self._log(f"   💡 Или добавьте новые алиасы в FIELD_ALIASES в начале скрипта", "info")
        
        self.root.after(0, lambda: self.process_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.status_var.set(
            f"Готово! Промптов: {total_prompts}, ошибок: {total_errors}"
        ))
    
    def _log_detailed_error(self, err: DetailedError):
        """Выводит детальную ошибку в лог."""
        preview = err.response_preview[:100].replace('\n', '↵').replace('\r', '')
        if len(err.response_preview) > 100:
            preview += "..."
        
        self._log(f"   ❌ [{err.error_type}] {err.task_id} ({err.task_name})", "error")
        self._log(f"      Причина: {err.error_message}", "dim")
        self._log(f"      Response ({err.response_length} симв.): {preview}", "dim")
        
        if err.suggestions:
            self._log(f"      💡 {err.suggestions[0]}", "info")
    
    def _save_outputs(
        self,
        technical_data: dict,
        prompts: list[str],
        input_path: str,
        parser: RobustJsonParser
    ) -> list[Path]:
        """Сохраняет результаты."""
        
        input_file = Path(input_path)
        output_folder = Path(self.output_dir) if self.output_dir else input_file.parent
        output_folder.mkdir(parents=True, exist_ok=True)
        
        base_name = input_file.stem
        saved_files = []
        
        # JSON с техническими данными
        tech_file = output_folder / f"{base_name}_technical.json"
        with open(tech_file, 'w', encoding='utf-8') as f:
            json.dump(technical_data, f, ensure_ascii=False, indent=2)
        saved_files.append(tech_file)
        
        # TXT с промптами
        prompts_file = output_folder / f"{base_name}_prompts.txt"
        with open(prompts_file, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(prompts))
        saved_files.append(prompts_file)
        
        # JSON с детальными ошибками (если есть)
        if parser.detailed_errors:
            errors_file = output_folder / f"{base_name}_errors.json"
            error_summary = parser.get_error_summary()
            
            errors_data = {
                "file": input_file.name,
                "summary": error_summary,
                "field_aliases_config": FIELD_ALIASES,
                "errors": [err.to_dict() for err in parser.detailed_errors]
            }
            
            with open(errors_file, 'w', encoding='utf-8') as f:
                json.dump(errors_data, f, ensure_ascii=False, indent=2)
            saved_files.append(errors_file)
        
        return saved_files


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    root = tk.Tk()
    
    style = ttk.Style()
    try:
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    
    app = VDParserApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
