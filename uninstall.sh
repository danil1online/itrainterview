#!/usr/bin/env bash
# Удаление системы: контейнеры, volumes (БД) и, опционально, образы.
# Исходники и .env не удаляются (для полного сноса — удалите каталог вручную).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

COMPOSE=""
if docker compose version >/dev/null 2>&1; then COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then COMPOSE="docker-compose"
else echo "docker compose не найден"; exit 1; fi

PURGE_IMAGES=${1:-}

SUDO_CMD=""
if [[ $EUID -ne 0 ]] && command -v sudo >/dev/null 2>&1; then SUDO_CMD="sudo"; fi

echo "Остановка контейнеров и удаление данных БД…"
$COMPOSE down -v --remove-orphans

if [[ "$PURGE_IMAGES" == "--purge" ]]; then
  echo "Удаление образов itrainterview/*…"
  docker images --format '{{.Repository}}:{{.Tag}}' | grep '^itrainterview/' | xargs -r docker rmi -f || true
  if [[ -d sandbox-work ]]; then
    echo "Очистка данных песочницы (sandbox-work)…"
    $SUDO_CMD rm -rf sandbox-work 2>/dev/null || rm -rf sandbox-work || true
  fi
fi

echo "Готово."
