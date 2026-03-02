# Exam Engine (Vue + Django)

Платформа для тестирования и обучения с админкой `/admin`, БД и статистикой по пользователям.

## Что сделано

- Vue SPA интерфейс (экзамены, обучение, рейтинг, спринт)
- Django backend API (`/api/...`)
- Админка Django (`/admin`) для обычного CRUD экзаменов, вопросов и вариантов
- Тайминг: время по умолчанию на вопрос в экзамене + индивидуальный override на уровне вопроса
- Статистика попыток пользователей (время, балл, верные ответы, число попыток)
- БД: SQLite по умолчанию, поддержка PostgreSQL/MySQL через env

## Backend

### 1. Установка

```bash
python -m pip install -r backend/requirements.txt
```

### 2. Миграции

```bash
python backend/manage.py migrate
```

### 3. Создать админа

```bash
python backend/manage.py createsuperuser
```

### 4. Запуск API и admin

```bash
python backend/manage.py runserver
```

- Admin: `http://127.0.0.1:8000/admin/`
- API: `http://127.0.0.1:8000/api/`

## Frontend

### 1. Установка

```bash
npm install
```

### 2. Запуск

```bash
npm run dev
```

По умолчанию frontend обращается к `http://127.0.0.1:8000/api`.
При необходимости укажи `VITE_API_BASE_URL`.

## Docker / VPS

- Быстрый деплой на Ubuntu VPS: см. [docs/DEPLOY_VPS.md](docs/DEPLOY_VPS.md)
- Итог изменений финальной сборки: [docs/CHANGELOG_FINAL.md](docs/CHANGELOG_FINAL.md)
- Запуск в одну команду:

Linux / Ubuntu:

```bash
sh scripts/install.sh
```

Если в `.env.docker` заданы `DOMAIN` и `LETSENCRYPT_EMAIL`,
скрипт автоматически настроит HTTPS через host nginx + Let's Encrypt.

One-liner для VPS (curl | sh):

```bash
curl -fsSL <RAW_BOOTSTRAP_URL> | REPO_URL=https://github.com/<user>/<repo>.git BRANCH=main APP_DIR=$HOME/apps/pet-exam sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

- Ручной запуск контейнеров:

```bash
cp .env.docker.example .env.docker
docker compose -p pet-exam up -d --build
```

Важно: переменные публикации порта (`APP_BIND_IP`, `APP_PORT`) берутся из `.env`
(файл генерируется скриптом `install.sh` автоматически из `.env.docker`).

## Конфиг БД

Смотри шаблон: `backend/.env.example`

- `DB_ENGINE=sqlite` (по умолчанию)
- `DB_ENGINE=postgresql`
- `DB_ENGINE=mysql`

## API (основное)

- `GET /api/exams/` - список экзаменов
- `GET /api/exams/{id}/` - экзамен с вопросами
- `POST /api/exams/{id}/submit/` - отправка попытки
- `GET /api/stats/users/` - сводная статистика по пользователям
- `GET /api/stats/attempts/` - список последних попыток

## Структура

- `backend/backend/settings.py` - настройки Django + DB/CORS
- `backend/exams/models.py` - модели экзаменов, попыток и ответов
- `backend/exams/admin.py` - админка
- `backend/exams/views.py` - API
- `backend/exams/urls.py` - роуты API
- `src/App.vue` - клиентский интерфейс
- `src/lib/api.ts` - клиент API
