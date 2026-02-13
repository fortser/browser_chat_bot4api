# ChatFlow Automator

Система автоматизации взаимодействия с веб-чатами.

## Возможности

- Автоматизация взаимодействия с чат-интерфейсами через браузер
- Поддержка прокси (HTTP/HTTPS/SOCKS5)
- Импорт/экспорт cookies
- Создание последовательностей задач (карточек)
- Сохранение результатов в JSON/Markdown/CSV
- Графический интерфейс на PyQt6

## Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd chatflow-automator

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -e ".[dev]"

# Установка браузеров Playwright
playwright install chromium
