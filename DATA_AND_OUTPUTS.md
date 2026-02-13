# 📊 Описание данных и выходных результатов

**Дата:** 13 февраля 2026 г., 19:21 | **Версия:** 1.0

---

## 📂 Структура папки DATA/

### 🔧 config.json — Главная конфигурация

**Путь:** `data/config.json`
**Назначение:** Центральная конфигурация всего приложения
**Используется:** Всеми модулями при инициализации

**Основные параметры:**
```json
{
  "browser": {
    "headless": true/false,
    "timeout": 30,
    "viewport": {"width": 1920, "height": 1080}
  },
  "proxy": {
    "enabled": true/false,
    "type": "http|socks5",
    "url": "proxy.example.com:8080"
  },
  "adapters": {
    "enabled": ["chatgpt", "claude", "genspark"],
    "default": "chatgpt"
  },
  "paths": {
    "cookies": "data/cookies/",
    "results": "data/results/",
    "tasks": "data/tasks/"
  }
}
```

---

### 🍪 cookies/ — Сохраненные сессии

**Путь:** `data/cookies/`
**Количество файлов:** 7
**Форматы:** JSON
**Использование:** Авторизация в чат-системах без повторного входа

#### Содержимые cookies:

| Файл | Домен | Статус |
|------|-------|--------|
| `2chatgpt.com.json` | ChatGPT (альт домен) | ✅ |
| `chat.qwen.ai_cookies.json` | Qwen AI | ✅ |
| `chatgpt.com_cookies.json` | ChatGPT основной | ✅ |
| `genspark.ai.json` | GenSpark AI | ✅ |
| `genspark.ai_cookies.json` | GenSpark AI (alt) | ✅ |
| `www.genspark.ai_cookies.json` | GenSpark (www) | ✅ |

**Структура JSON cookies:**
```json
[
  {
    "name": "cookie_name",
    "value": "cookie_value",
    "domain": ".example.com",
    "path": "/",
    "expires": 1735689600,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  }
]
```

**Как использовать:**
```python
from src.chatflow.browser.cookies import CookieManager

manager = CookieManager()
cookies = manager.load_cookies('data/cookies/chatgpt.com_cookies.json')
```

---

### 📈 results/ — Результаты выполнения

**Путь:** `data/results/`
**Количество файлов:** 80+
**Форматы:** JSON, Markdown, TXT
**Назначение:** Сохранение результатов выполнения задач

#### Типы файлов результатов:

##### 1. **session_*.json** — Основные результаты
**Формат:** JSON (структурированные данные)
**Содержание:**
```json
{
  "session_id": "session_20260130_115930",
  "start_time": "2026-01-30T11:59:30",
  "end_time": "2026-01-30T12:05:45",
  "status": "completed",
  "tasks_total": 5,
  "tasks_completed": 5,
  "tasks_failed": 0,
  "results": [
    {
      "task_id": "task_001",
      "prompt": "What is AI?",
      "response": "Artificial Intelligence is...",
      "duration": 2.34,
      "adapter": "chatgpt",
      "status": "success"
    }
  ]
}
```

##### 2. **session_*_prompts.txt** — Список использованных промптов
**Формат:** TXT (простой текст)
**Пример:**
```
SESSION: session_20260130_192034

Task 1: Explain quantum computing
Task 2: What is machine learning?
Task 3: Difference between AI and ML
...
```

##### 3. **session_*_technical.json** — Техническая информация
**Назначение:** Отладка и анализ производительности
**Содержание:**
```json
{
  "session_id": "session_20260130_192034",
  "technical": {
    "browser": "chromium",
    "playwright_version": "1.40.0",
    "proxy_used": false,
    "memory_usage_mb": 245,
    "cpu_percent": 12.5,
    "network_latency_ms": 45
  },
  "errors": [],
  "warnings": []
}
```

##### 4. **session_*.md** — Markdown отчет
**Назначение:** Читаемый отчет
**Пример:**
```markdown
# Session Report: 20260130_191315

## Summary
- Start: 2026-01-30 19:13:15
- Duration: 5m 42s
- Status: ✅ Completed

## Results
### Task 1: Explain quantum computing
**Response:** Quantum computing uses quantum...

### Task 2: What is machine learning?
**Response:** Machine learning is a subset...
```

##### 5. **session_*_errors.json** — Логи ошибок
**Назначение:** Анализ сбоев
**Содержание:**
```json
{
  "session_id": "session_20260202_183804",
  "errors": [
    {
      "task_id": "task_003",
      "error_type": "TimeoutError",
      "message": "Browser timeout after 30s",
      "timestamp": "2026-02-02T18:38:15",
      "traceback": "..."
    }
  ],
  "error_count": 1,
  "warning_count": 3
}
```

#### Примеры файлов (реальные):
```
✓ session_20260130_115930.json
✓ session_20260130_120633.json
✓ session_20260130_121120.json
✓ session_20260130_124352.json
✓ session_20260130_131034.json
✓ session_20260130_132637.json
✓ session_20260130_134822.json
✓ session_20260130_134903.json
✓ session_20260130_185234.json
✓ session_20260130_192034.json
✓ session_20260130_192034_prompts.txt
✓ session_20260130_192034_technical.json
✓ session_20260130_191315.md
✓ session_20260202_183804.json
✓ session_20260202_183804_errors.json
... и еще 65+ файлов
```

---

### 📝 logs/ — Логи выполнения

**Путь:** `data/logs/`
**Формат:** TXT с временными метками
**Назначение:** Отладка и мониторинг

**Примерный формат логов:**
```
[2026-02-13 19:21:45] INFO: Starting ChatFlow Automator v0.1.0
[2026-02-13 19:21:46] INFO: Loading configuration from data/config.json
[2026-02-13 19:21:47] INFO: Initializing browser with Playwright
[2026-02-13 19:21:48] INFO: Loaded 3 adapters: [chatgpt, claude, genspark]
[2026-02-13 19:21:49] INFO: Loaded 5 tasks from data/tasks/workflow.json
[2026-02-13 19:21:50] DEBUG: Connecting with proxy: disabled
[2026-02-13 19:21:51] INFO: Starting task execution
[2026-02-13 19:22:15] INFO: Task 1 completed successfully in 2.34s
[2026-02-13 19:22:45] WARNING: Task 2 took longer than expected (45s)
[2026-02-13 19:23:00] ERROR: Task 3 failed with TimeoutError
[2026-02-13 19:23:01] INFO: Session completed. Summary: 2/3 tasks successful
```

---

### 🎯 tasks/ — Сохраненные задачи

**Путь:** `data/tasks/`
**Формат:** JSON
**Назначение:** Сохранение и переиспользование последовательностей задач

**Структура файла задачи (task_workflow.json):**
```json
{
  "workflow_id": "workflow_001",
  "name": "Customer Support Analysis",
  "description": "Analyze customer feedback using different AI models",
  "created_at": "2026-02-13T19:21:00",
  "tasks": [
    {
      "id": "task_001",
      "prompt": "Summarize the following customer feedback: {feedback}",
      "adapter": "chatgpt",
      "variables": ["feedback"],
      "timeout": 30,
      "retries": 2,
      "order": 1
    },
    {
      "id": "task_002",
      "prompt": "Classify sentiment of: {text}",
      "adapter": "claude",
      "variables": ["text"],
      "timeout": 30,
      "retries": 2,
      "order": 2,
      "depends_on": ["task_001"]
    }
  ]
}
```

---

## 📤 ВЫХОДНЫЕ РЕЗУЛЬТАТЫ АНАЛИЗА

### 1. Результаты экспорта (storage/export/)

#### JSON Экспорт
**Файл:** `results_export.json`
**Использование:** Программная обработка результатов
```json
{
  "export_type": "json",
  "session_count": 45,
  "total_tasks": 234,
  "success_rate": 0.95,
  "sessions": [...]
}
```

#### CSV Экспорт
**Файл:** `results_export.csv`
**Использование:** Анализ в Excel/Sheets
```
session_id,task_id,status,duration_s,adapter,timestamp
session_20260130_115930,task_001,success,2.34,chatgpt,2026-01-30T11:59:45
session_20260130_115930,task_002,success,3.12,claude,2026-01-30T12:00:12
```

#### Markdown Экспорт
**Файл:** `results_report.md`
**Использование:** Человеческий отчет
```markdown
# ChatFlow Execution Report

## Statistics
- Total Sessions: 45
- Total Tasks: 234
- Success Rate: 95%
- Average Duration: 2.87s

## Sessions Summary
| Session | Tasks | Status | Duration |
|---------|-------|--------|----------|
| 001 | 5 | ✅ | 15m 23s |
| 002 | 5 | ✅ | 14m 51s |
```

---

### 2. Статистика по адаптерам

**Сохраняется в:** `data/results/statistics.json`

```json
{
  "adapters_stats": {
    "chatgpt": {
      "total_tasks": 100,
      "successful": 95,
      "failed": 5,
      "avg_response_time_s": 2.45,
      "error_rate": 0.05
    },
    "claude": {
      "total_tasks": 85,
      "successful": 83,
      "failed": 2,
      "avg_response_time_s": 2.67,
      "error_rate": 0.024
    },
    "genspark": {
      "total_tasks": 49,
      "successful": 47,
      "failed": 2,
      "avg_response_time_s": 3.12,
      "error_rate": 0.041
    }
  }
}
```

---

### 3. История выполнения

**Путь:** `src/chatflow/storage/history.py`
**Назначение:** Отслеживание состояния между сеансами

**Сохраняется как:** `.cache/chatflow_history.json`

```json
{
  "last_execution": "2026-02-13T19:21:30",
  "last_session_id": "session_20260213_192130",
  "total_sessions": 47,
  "total_tasks_executed": 251,
  "uptime_hours": 124.5,
  "recent_errors": [
    {
      "timestamp": "2026-02-13T19:20:15",
      "error": "BrowserError: Connection refused",
      "session": "session_20260213_192015"
    }
  ]
}
```

---

## 🎯 Типичные выходные файлы

### После одного сеанса выполнения:

```
data/results/
├── session_20260213_192130.json              [основной результат]
├── session_20260213_192130_prompts.txt       [использованные промпты]
├── session_20260213_192130_technical.json    [техническая инфо]
└── session_20260213_192130.md                [отчет в Markdown]
```

### После нескольких сеансов:

```
data/results/
├── summary_weekly.json                       [еженедельная сводка]
├── summary_monthly.json                      [ежемесячная сводка]
├── export_all_results.csv                    [полный экспорт]
├── performance_report.md                     [отчет производительности]
└── error_analysis.json                       [анализ ошибок]
```

---

## 📊 Метрики и статистика

### Сохраняемые метрики:

| Метрика | Где сохраняется | Тип данных |
|---------|-----------------|-----------|
| Время выполнения | session_*.json | float (секунды) |
| Статус задачи | session_*.json | enum (success/fail/timeout) |
| Использованный адаптер | session_*.json | string |
| Промпт и ответ | session_*_prompts.txt | text |
| Ошибки | session_*_errors.json | array |
| Потребление памяти | session_*_technical.json | int (MB) |
| Версия браузера | session_*_technical.json | string |
| Задержка сети | session_*_technical.json | int (ms) |

---

## 🔄 Жизненный цикл файла результата

```
1. Выполнение задачи
        ↓
2. Сбор результатов (core/engine.py)
        ↓
3. Создание session_*.json
        ↓
4. Выполнение валидации
        ↓
5. Создание доп. файлов (_prompts.txt, _technical.json)
        ↓
6. Логирование в logs/
        ↓
7. Обновление истории (storage/history.py)
        ↓
8. Экспорт (если включен)
        ↓
9. GUI отображение (gui/widgets/results_tab.py)
```

---

## 💾 Размеры файлов

| Тип | Размер | Примечание |
|-----|--------|-----------|
| Один session_*.json | 10-50 KB | Зависит от кол-ва задач |
| session_*_technical.json | 2-5 KB | Постоянный размер |
| Markdown отчет | 5-20 KB | Зависит от деталей |
| Cookies файл | 5-15 KB | Перезаписывается |
| Config.json | 2-5 KB | Конфигурация |

**Общее использование дискового пространства:**
- 80+ sessions: ~4 MB
- Cookies (7 файлов): ~80 KB
- Logs: ~10 MB (зависит от времени работы)
- Итого: ~15 MB (для текущего состояния)

---

## 🔐 Безопасность данных

### Чувствительные данные в results:
- ✅ **Cookies** — зашифрованы/защищены от Git (.gitignore)
- ✅ **Промпты** — могут содержать конфиденциальную информацию
- ✅ **Config** — содержит данные прокси и API

### Рекомендации:
```bash
# Добавить в .gitignore:
data/cookies/
data/config.json
data/results/
```

---

## 📋 Чек-лист анализа данных

```
☑ session_*.json — основной результат, проверить status
☑ session_*_errors.json — есть ли ошибки, их количество
☑ session_*_technical.json — потребление ресурсов
☑ logs/ — последовательность событий
☑ cookies/ — наличие сохраненных сессий
☑ tasks/ — сохраненные workflow-ы
```

---

*Документ актуален на 13 февраля 2026 г., 19:21*
