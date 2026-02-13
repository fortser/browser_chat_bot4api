# 🗂️ Быстрая схема структуры проекта ChatFlow Automator

**Обновлено:** 13.02.2026 19:21 | **Всего файлов:** 7398

---

## 📌 Структура папок

```
test_python/
└── bro_bot/
    ├── 🟢 chatflow-automator/              [ОСНОВНОЙ ПРОЕКТ]
    │   ├── 📄 README.md                    → Документация
    │   ├── 📄 pyproject.toml               → Зависимости и конфиг
    │   ├── 📄 card_editor.py               → Редактор карточек (PyQt6)
    │   ├── 📄 vd_parser.py                 → Парсер данных
    │   ├── 🟡 docs/                        → Документация
    │   ├── 🟡 examples/                    → Примеры конфигураций
    │   ├── 🔵 tests/                       → Тесты (unit + integration)
    │   ├── 🟠 src/chatflow/                → ОСНОВНОЙ КОД
    │   │   ├── adapters/                   → Адаптеры чатов (ChatGPT, Claude, etc)
    │   │   ├── browser/                    → Управление браузером (Playwright)
    │   │   ├── cli/                        → CLI интерфейс
    │   │   ├── core/                       → Ядро (engine, events, types)
    │   │   ├── gui/                        → PyQt6 интерфейс
    │   │   ├── storage/                    → Сохранение (config, results, export)
    │   │   ├── tasks/                      → Работа с задачами
    │   │   └── utils/                      → Утилиты
    │   ├── 🟣 data/                        → Данные и результаты
    │   │   ├── config.json                 → Главная конфигурация
    │   │   ├── cookies/                    → Сохраненные cookies (7 файлов)
    │   │   ├── results/                    → Результаты (80+ JSON/MD/TXT)
    │   │   ├── logs/                       → Логи выполнения
    │   │   └── tasks/                      → Сохраненные задачи
    │   ├── 🗑️ card_editor_parser_old_copies/ → Старые копии (архив)
    │   ├── 🟠 venv/                        → Python окружение (6000+ файлов)
    │   └── GO-*.BAT                        → Батники запуска
    │
    ├── 🟣 cookie_extractor/                [ОТДЕЛЬНЫЙ ПРОЕКТ]
    │   ├── step1.py                        → Извлечение cookies
    │   ├── step2.py                        → Обработка cookies
    │   ├── *.sqlite                        → Базы cookies
    │   └── CookBaseParser.bat
    │
    └── 🟢 Корневые файлы
        ├── claude_start.bat
        └── GO.BAT
```

---

## 🎯 Основные компоненты

### 1️⃣ АДАПТЕРЫ (src/chatflow/adapters/)
```
Назначение: Взаимодействие с разными чат-платформами

🔗 Наследование:
    base.py (BaseAdapter)
        ├─ chatgpt.py (ChatGPTAdapter)
        ├─ claude.py (ClaudeAdapter)
        ├─ genspark.py (GenSparkAdapter)
        ├─ qwen.py (QwenAdapter)
        └─ generic.py (GenericAdapter)
```

### 2️⃣ БРАУЗЕР (src/chatflow/browser/)
```
Назначение: Управление Playwright браузером

🔗 Связь:
    manager.py ◄─► actions.py
        │
        ├─ cookies.py
        ├─ stealth.py (Anti-detection)
        └─ threadsafe_browser.py
```

### 3️⃣ ЯДРО (src/chatflow/core/)
```
Назначение: Центральная логика выполнения

🔗 Структура:
    engine.py ◄─► async_worker.py
        │
        ├─ events.py
        ├─ exceptions.py
        └─ types.py (Pydantic models)
```

### 4️⃣ GUI (src/chatflow/gui/)
```
Назначение: PyQt6 интерфейс

🔗 Иерархия:
    app.py
        │
        ├─ main_window.py ◄─► utils.py
        │       │
        │       ├─ widgets/
        │       │   ├─ connection_tab.py
        │       │   ├─ execution_tab.py
        │       │   ├─ tasks_tab.py
        │       │   ├─ results_tab.py
        │       │   └─ log_viewer.py
        │       │
        │       └─ dialogs/
        │           ├─ import_dialog.py
        │           ├─ export_dialog.py
        │           └─ settings_dialog.py
```

### 5️⃣ ХРАНЕНИЕ (src/chatflow/storage/)
```
Назначение: Сохранение конфигов и результатов

🔗 Зависимости:
    config.py ◄─── Загрузка конфигов
    results.py ◄─── Сохранение результатов

    export/
        ├─ base.py
        ├─ json_export.py
        ├─ csv_export.py
        └─ markdown_export.py
```

### 6️⃣ ЗАДАЧИ (src/chatflow/tasks/)
```
Назначение: Работа с последовательностями задач

🔗 Flow:
    loader.py ──► models.py ──► validator.py ──► executor.py
                      │                              │
                      └──────► variables.py ◄────────┘
```

---

## 📊 Группировка файлов по важности

### 🟢 КРИТИЧЕСКИЕ (без них не работает)
```
✓ src/chatflow/core/engine.py
✓ src/chatflow/browser/manager.py
✓ src/chatflow/tasks/executor.py
✓ src/chatflow/adapters/base.py
✓ src/chatflow/tasks/models.py
✓ pyproject.toml
```

### 🟡 ВАЖНЫЕ (основной функционал)
```
✓ src/chatflow/gui/main_window.py
✓ src/chatflow/storage/config.py
✓ src/chatflow/storage/results.py
✓ src/chatflow/adapters/*
✓ src/chatflow/cli/commands.py
✓ src/chatflow/tasks/*
```

### 🔵 ПОДДЕРЖИВАЮЩИЕ (улучшения)
```
✓ src/chatflow/browser/stealth.py
✓ src/chatflow/browser/cookies.py
✓ src/chatflow/gui/dialogs/*
✓ src/chatflow/gui/widgets/*
✓ src/chatflow/storage/export/*
✓ src/chatflow/utils/*
```

### 🟣 ОПЦИОНАЛЬНЫЕ (не критичны)
```
✓ tests/*
✓ docs/*
✓ examples/*
✓ card_editor.py (standalone)
✓ vd_parser.py (standalone)
```

### 🗑️ УСТАРЕВШИЕ (удалить)
```
✗ card_editor_parser_old_copies/*
✗ src/chatflow/gui/main_window — копия.py
✗ src/chatflow/gui/widgets/execution_tab — копия.py
✗ cookie_extractor/*_copy.py
```

---

## 🔄 Процесс выполнения задачи

```
1. Пользователь → GUI (gui/main_window.py)
                    ↓
2. Ввод параметров → tasks_tab.py, connection_tab.py
                    ↓
3. Загрузка задач → tasks/loader.py + validator.py
                    ↓
4. Инициализация → core/engine.py + browser/manager.py
                    ↓
5. Запуск → tasks/executor.py
             ↓
6. Цикл задач:
   a) Выбрать адаптер (adapters/*)
   b) Открыть браузер (browser/actions.py)
   c) Обработать переменные (tasks/variables.py)
   d) Выполнить действие
   e) Парсить результат
   f) Логировать (core/events.py)
             ↓
7. Сохранить результаты → storage/results.py
                    ↓
8. Экспортировать → storage/export/*
                    ↓
9. Показать в GUI → results_tab.py + log_viewer.py
```

---

## 📈 Статистика кода

| Компонент | Файлов | Строк | Назначение |
|-----------|--------|-------|-----------|
| adapters | 7 | ~1500 | Чат-платформы |
| browser | 5 | ~1200 | Браузер |
| core | 5 | ~1800 | Ядро |
| gui | 14 | ~3500 | Интерфейс |
| storage | 8 | ~1000 | Хранение |
| tasks | 6 | ~1500 | Задачи |
| cli | 2 | ~500 | CLI |
| utils | 4 | ~400 | Утилиты |
| tests | 8 | ~2000 | Тесты |
| **ИТОГО** | **65** | **~13500** | Основной код |

---

## 🚀 Быстрый старт для разработчика

### 📖 1. Понимание архитектуры (15 минут)
```bash
# Прочитать в этом порядке:
1. README.md                      # Общее описание
2. pyproject.toml                 # Зависимости
3. src/chatflow/core/engine.py    # Главный движок
4. src/chatflow/core/types.py     # Модели данных
```

### 🔌 2. Добавить новый чат (30 минут)
```bash
# Скопировать и адаптировать:
1. src/chatflow/adapters/generic.py  → mychat.py
2. Наследовать от base.py
3. Реализовать методы для своего чата
4. Зарегистрировать в __init__.py
```

### 🎨 3. Добавить опцию GUI (20 минут)
```bash
# Модифицировать:
1. src/chatflow/gui/widgets/connection_tab.py    # Добавить поле
2. src/chatflow/gui/main_window.py              # Подключить сигнал
3. src/chatflow/core/types.py                   # Добавить в ConfigModel
```

### 📤 4. Добавить экспортер (25 минут)
```bash
# Создать:
1. src/chatflow/storage/export/myformat_export.py
2. Наследовать от base.py
3. Реализовать метод export()
4. Зарегистрировать в results.py
```

### ✅ 5. Написать тесты (20 минут)
```bash
# Добавить:
1. tests/unit/test_mychat.py
2. tests/integration/test_mychat_integration.py
3. Запустить: pytest -v
```

---

## 🔍 Поиск кода

### Где найти функцию?
```
Отправка сообщения в чат?
→ src/chatflow/adapters/[chat_name].py

Управление браузером?
→ src/chatflow/browser/actions.py

Валидация задач?
→ src/chatflow/tasks/validator.py

Логирование событий?
→ src/chatflow/core/events.py

Работа с конфигом?
→ src/chatflow/storage/config.py

GUI кнопки?
→ src/chatflow/gui/widgets/
```

---

## 🛠️ Инструменты для работы

```
Запуск GUI:
  python -m chatflow          (или chatflow-gui)
  или
  GO-card_editor.BAT

Запуск CLI:
  chatflow --help

Запуск парсера:
  python vd_parser.py
  или
  GO-parser.BAT

Запуск редактора:
  python card_editor.py

Тесты:
  pytest                      (все тесты)
  pytest tests/unit/          (unit тесты)
  pytest tests/integration/   (интеграционные)
  pytest -v                   (подробно)
```

---

## 📞 Файлы для конфигурации

```
Основная конфигурация:
  → data/config.json

Пример конфигурации:
  → examples/config_example.json

Задачи:
  → data/tasks/*.json
  → examples/simple_workflow.json

Cookies:
  → data/cookies/[domain].json
```

---

*Последнее обновление: 13 февраля 2026 | Подробный анализ см. в PROJECT_STRUCTURE_ANALYSIS.md*
