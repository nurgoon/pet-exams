# Deploy на Ubuntu VPS (Docker) — пошагово

Этот гайд рассчитан на запуск **нескольких pet/self-hosted проектов** на одном сервере без конфликтов.

## 1. Что уже подготовлено в проекте

- `docker-compose.yml` — backend + frontend
- `scripts/install.sh` — one-command запуск (создает `.env.docker`, если его нет)
- `backend/Dockerfile` — Django + gunicorn
- `backend/entrypoint.sh` — `migrate` + `collectstatic` + запуск gunicorn
- `Dockerfile` (root) + `deploy/nginx/default.conf` — сборка Vue SPA + nginx reverse proxy к backend
- `.env.docker.example` — шаблон прод-конфига

## 2. Установка Docker на Ubuntu

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

## 3. Размещение проекта

```bash
mkdir -p ~/apps/pet-exam
cd ~/apps/pet-exam
# сюда копируешь/клонируешь проект
```

Рекомендуемая структура на VPS:
- `~/apps/pet-exam`
- `~/apps/another-project`
- `~/apps/selfhosted-tool`

## 4. Подготовка env

```bash
cd ~/apps/pet-exam
cp .env.docker.example .env.docker
nano .env.docker
```

Минимально обязательно поменять:
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `CORS_ALLOWED_ORIGINS`
- `APP_PORT` (уникальный порт для этого проекта)

Для автоматического HTTPS (Let's Encrypt) дополнительно укажи:
- `DOMAIN` (например `grade.alwaysinit.ru`)
- `LETSENCRYPT_EMAIL` (твой email для LE)

Пример без конфликтов:
- проект A: `APP_PORT=18080`
- проект B: `APP_PORT=18081`
- проект C: `APP_PORT=18082`

## 5. Первый запуск

Быстрый вариант (одной командой):

```bash
sh scripts/install.sh
```

Что делает `install.sh`:
- создает `.env.docker` из шаблона при первом запуске
- синхронизирует переменные `APP_BIND_IP/APP_PORT` в `.env` для `docker compose`
- при наличии `DOMAIN` + `LETSENCRYPT_EMAIL` автоматически настраивает host nginx + certbot

One-liner вариант (`curl | sh`):

```bash
curl -fsSL <RAW_BOOTSTRAP_URL> | REPO_URL=https://github.com/<user>/<repo>.git BRANCH=main APP_DIR=$HOME/apps/pet-exam sh
```

Где:
- `<RAW_BOOTSTRAP_URL>` — raw-ссылка на `scripts/bootstrap.sh` в твоем репозитории.

Или вручную:

```bash
docker compose -p pet-exam up -d --build
```

Пояснение:
- `-p pet-exam` задает уникальное имя проекта Docker (сети/контейнеры не конфликтуют с другими).

Проверка:
```bash
docker compose -p pet-exam ps
docker compose -p pet-exam logs -f backend
docker compose -p pet-exam logs -f frontend
```

## 6. Создать суперпользователя

```bash
docker compose -p pet-exam exec backend python manage.py createsuperuser
```

## 7. Открыть приложение

- Сайт: `http://SERVER_IP:APP_PORT`
- Админка: `http://SERVER_IP:APP_PORT/admin/`
- API: `http://SERVER_IP:APP_PORT/api/`

Если настроены `DOMAIN` и `LETSENCRYPT_EMAIL`, используй:
- `https://DOMAIN`
- `https://DOMAIN/admin/`

## 8. Обновление приложения

```bash
cd ~/apps/pet-exam
# git pull (если используешь git)
docker compose -p pet-exam up -d --build
```

Миграции/статика выполняются автоматически в `entrypoint.sh`.

## 9. Резервное копирование (SQLite)

База лежит в `backend/db.sqlite3` (bind mount).

```bash
cd ~/apps/pet-exam
cp backend/db.sqlite3 backup_$(date +%F_%H-%M).sqlite3
```

## 10. Как избежать конфликтов с другими проектами

Всегда соблюдай 4 правила:

1. Уникальный `APP_PORT` для каждого проекта.
2. Уникальный Docker project name: `docker compose -p <unique-name> ...`.
3. Отдельная директория проекта (`~/apps/<project>`).
4. Отдельный `.env.docker` для каждого проекта.

## 11. Домен без порта (из коробки)

В этом проекте можно без ручной настройки:
- `install.sh` автоматически настраивает системный `nginx` как reverse proxy
- `certbot` автоматически получает и обновляет сертификат Let's Encrypt
- фронт и `/admin` доступны по `https://DOMAIN`

Требования:
- DNS `A/AAAA` для `DOMAIN` указывает на VPS
- на сервере открыты порты `80` и `443`
- в `.env.docker` заполнены `DOMAIN` и `LETSENCRYPT_EMAIL`
