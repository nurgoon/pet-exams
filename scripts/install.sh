#!/usr/bin/env sh
set -e

PROJECT_NAME=${COMPOSE_PROJECT_NAME:-pet-exams}
ENV_FILE=.env.docker
ENV_EXAMPLE=.env.docker.example
COMPOSE_ENV_FILE=.env

append_csv_unique() {
  list="$1"
  item="$2"
  found=0
  out=""
  old_ifs=$IFS
  IFS=','
  for part in $list; do
    [ -z "$part" ] && continue
    if [ "$part" = "$item" ]; then
      found=1
    fi
    if [ -z "$out" ]; then
      out="$part"
    else
      out="$out,$part"
    fi
  done
  IFS=$old_ifs
  if [ "$found" -eq 0 ]; then
    if [ -n "$out" ]; then
      out="$out,$item"
    else
      out="$item"
    fi
  fi
  echo "$out"
}

set_env_var() {
  key="$1"
  value="$2"
  tmp_file="${ENV_FILE}.tmp"
  awk -v k="$key" -v v="$value" '
    BEGIN { done=0 }
    $0 ~ ("^" k "=") { print k "=" v; done=1; next }
    { print }
    END { if (!done) print k "=" v }
  ' "$ENV_FILE" > "$tmp_file"
  mv "$tmp_file" "$ENV_FILE"
}

run_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "Root permissions are required to install Docker (no sudo found)." >&2
    exit 1
  fi
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    return 0
  fi

  if ! command -v curl >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      run_root apt-get update
      run_root apt-get install -y curl ca-certificates
    else
      echo "curl is required to install Docker automatically." >&2
      exit 1
    fi
  fi

  echo "Docker/compose not found. Installing Docker Engine..."
  curl -fsSL https://get.docker.com | run_root sh

  if command -v systemctl >/dev/null 2>&1; then
    run_root systemctl enable --now docker || true
  fi

  if ! docker compose version >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      run_root apt-get update
      run_root apt-get install -y docker-compose-plugin
    else
      echo "docker compose plugin is not installed and could not be installed automatically." >&2
      exit 1
    fi
  fi
}

ensure_docker

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

if [ -n "$DOMAIN" ]; then
  DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1}
  CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS:-}
  CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-}

  DJANGO_ALLOWED_HOSTS=$(append_csv_unique "$DJANGO_ALLOWED_HOSTS" "$DOMAIN")
  CSRF_TRUSTED_ORIGINS=$(append_csv_unique "$CSRF_TRUSTED_ORIGINS" "https://$DOMAIN")
  CORS_ALLOWED_ORIGINS=$(append_csv_unique "$CORS_ALLOWED_ORIGINS" "https://$DOMAIN")

  set_env_var "DJANGO_ALLOWED_HOSTS" "$DJANGO_ALLOWED_HOSTS"
  set_env_var "CSRF_TRUSTED_ORIGINS" "$CSRF_TRUSTED_ORIGINS"
  set_env_var "CORS_ALLOWED_ORIGINS" "$CORS_ALLOWED_ORIGINS"
fi

cat > "$COMPOSE_ENV_FILE" <<EOF
APP_BIND_IP=$APP_BIND_IP
APP_PORT=$APP_PORT
EOF

echo "Starting containers (project: $PROJECT_NAME)..."
docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" up -d --build

echo "Waiting for backend health..."
retries=90
while [ "$retries" -gt 0 ]; do
  if docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" ps backend | grep -q "(healthy)"; then
    break
  fi
  retries=$((retries - 1))
  sleep 2
done

if [ "$retries" -eq 0 ]; then
  echo "Backend did not become healthy in time. Last backend logs:" >&2
  docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME" logs --tail=120 backend >&2 || true
  exit 1
fi

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
