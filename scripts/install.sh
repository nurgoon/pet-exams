#!/usr/bin/env sh
set -e

PROJECT_NAME=${COMPOSE_PROJECT_NAME:-pet-exam}
ENV_FILE=.env.docker
ENV_EXAMPLE=.env.docker.example
COMPOSE_ENV_FILE=.env

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed. Please install Docker first." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is not installed." >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "Missing $ENV_EXAMPLE" >&2
    exit 1
  fi
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Created $ENV_FILE from $ENV_EXAMPLE"
fi

if [ ! -f "./backend/db.sqlite3" ]; then
  touch "./backend/db.sqlite3"
fi

if [ -d "./backend/db.sqlite3" ]; then
  echo "./backend/db.sqlite3 is a directory. Remove it and create a file before deploy." >&2
  exit 1
fi

set -a
. "./$ENV_FILE"
set +a

APP_BIND_IP=${APP_BIND_IP:-127.0.0.1}
APP_PORT=${APP_PORT:-18080}
DOMAIN=${DOMAIN:-}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-}

cat > "$COMPOSE_ENV_FILE" <<EOF
APP_BIND_IP=$APP_BIND_IP
APP_PORT=$APP_PORT
EOF

echo "Starting containers (project: $PROJECT_NAME)..."
docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" up -d --build

echo "Application: http://$APP_BIND_IP:$APP_PORT"
echo "Admin: http://$APP_BIND_IP:$APP_PORT/admin/"

if [ -n "$DOMAIN" ] || [ -n "$LETSENCRYPT_EMAIL" ]; then
  if [ -z "$DOMAIN" ] || [ -z "$LETSENCRYPT_EMAIL" ]; then
    echo "DOMAIN and LETSENCRYPT_EMAIL must both be set for automatic SSL." >&2
    exit 1
  fi

  echo "Configuring HTTPS for $DOMAIN..."
  sh scripts/setup_ssl_nginx.sh "$DOMAIN" "$LETSENCRYPT_EMAIL" "$APP_PORT"
  echo "HTTPS enabled: https://$DOMAIN"
  echo "Admin: https://$DOMAIN/admin/"
fi
