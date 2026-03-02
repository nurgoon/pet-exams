#!/usr/bin/env sh
set -e

REPO_URL=${REPO_URL:-""}
BRANCH=${BRANCH:-main}
APP_DIR=${APP_DIR:-"$HOME/apps/pet-exam"}

if [ -z "$REPO_URL" ]; then
  echo "Укажите REPO_URL, например:" >&2
  echo "REPO_URL=https://github.com/<user>/<repo>.git sh bootstrap.sh" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git не найден. Установите git и повторите." >&2
  exit 1
fi

if [ -d "$APP_DIR/.git" ]; then
  echo "Обновляю существующий проект в $APP_DIR"
  git -C "$APP_DIR" fetch --all --prune
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
  echo "Клонирую проект в $APP_DIR"
  mkdir -p "$(dirname "$APP_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
sh scripts/install.sh
