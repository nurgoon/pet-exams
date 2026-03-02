#!/usr/bin/env sh
set -e

REPO_URL=${REPO_URL:-""}
BRANCH=${BRANCH:-main}
APP_DIR=${APP_DIR:-"$HOME/apps/pet-exams"}

run_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "Root privileges are required to install Docker. Run as root or install sudo." >&2
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
      echo "curl was not found. Install curl manually and retry." >&2
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
      echo "Could not install docker compose plugin automatically." >&2
      exit 1
    fi
  fi
}

if [ -z "$REPO_URL" ]; then
  echo "Set REPO_URL, for example:" >&2
  echo "REPO_URL=https://github.com/<user>/<repo>.git sh bootstrap.sh" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    run_root apt-get update
    run_root apt-get install -y git
  else
    echo "git was not found. Install git and retry." >&2
    exit 1
  fi
fi

ensure_docker

if [ -d "$APP_DIR/.git" ]; then
  echo "Updating existing project in $APP_DIR"
  git -C "$APP_DIR" fetch --all --prune
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
  echo "Cloning project into $APP_DIR"
  mkdir -p "$(dirname "$APP_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
sh scripts/install.sh
