# Hirify MCP Server 🔍💼

MCP (Model Context Protocol) сервер для поиска и сопоставления вакансий с платформы [Hirify.me](https://hirify.me) с использованием стелс-скрапера [Scrapling](https://github.com/D4Vinci/Scrapling).

## Возможности

- 📄 **Анализ профиля и резюме (`parse_profile`)**: извлекает стек технологий, грейд (Junior/Middle/Senior/Lead), роли и предпочтения по формату работы.
- 🎯 **Умный подбор вакансий (`match_vacancies`)**: анализирует вакансии на Hirify, рассчитывает совместимость (0–100%) по стеку, грейду и формату, возвращает топ подходящих вакансий с разбором плюсов, минусов и ссылками/контактами.
- 🔎 **Поиск вакансий (`search_vacancies`)**: прямой поиск по ключевым словам с фильтрами по грейду, формату (remote/hybrid/onsite) и специализации.
- 📋 **Детали вакансии (`get_vacancy_details`)**: получение полного текста вакансии, контактов рекрутеров и прямых ссылок для отклика.

## Установка и настройка

### 1. Установка окружения

Требуется Python >= 3.11:

```bash
uv pip install -e .
```

или через стандартный pip:

```bash
pip install -e .
```

### 2. Подключение в MCP-клиенты

#### Claude Desktop
Добавьте в ваш `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hirify": {
      "command": "path",
      "args": ["-m", "hirify_mcp.server"]
    }
  }
}
```

#### Cursor / Antigravity / Windsurf
В настройках MCP добавьте новый сервер типа `command`:
- **Command:** `C:\Users\"your_name"\Desktop\hirify_mcp\.venv\Scripts\python.exe`
- **Args:** `["-m", "hirify_mcp.server"]`

## Доступные инструменты (MCP Tools)

| Инструмент | Параметры | Описание |
| :--- | :--- | :--- |
| `match_vacancies` | `profile_text`, `top_n=10`, `work_format=None`, `grade=None`, `min_score=40` | Главный инструмент сопоставления резюме с вакансиями |
| `search_vacancies` | `query`, `grade=None`, `work_format=None`, `specialization=None`, `limit=15` | Поиск вакансий с фильтрами |
| `get_vacancy_details` | `vacancy_id` | Подробная информация и контакты вакансии |
| `parse_profile` | `text` | Извлечение структурированных данных из текста резюме |

## Запуск тестов

```bash
pytest tests/
```
