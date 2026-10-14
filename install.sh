#!/usr/bin/env bash
# ============================================================================
# ITInterview — установка/сборка системы на произвольном Ubuntu-сервере.
#
# Интерактивно запрашивает параметры (OpenAI-совместимый endpoint llama.cpp,
# порт, администратора), устанавливает Docker при необходимости, собирает
# образы и запускает систему через docker compose.
#
# Неинтерактивный режим:
#   ./install.sh --non-interactive \
#       --llm-url http://192.168.2.83:8080/v1 [--llm-model NAME] \
#       [--port 7777] [--admin-email admin@example.com] [--admin-password PASS] \
#       [--skip-llm-check] [--yes]
# ============================================================================
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$INSTALL_DIR"

LLM_URL="http://192.168.2.83:8080/v1"
LLM_MODEL=""
APP_PORT="7777"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD=""
NON_INTERACTIVE=0
SKIP_LLM_CHECK=0
ASSUME_YES=0

C_G="\033[32m"; C_Y="\033[33m"; C_R="\033[31m"; C_B="\033[1m"; C_0="\033[0m"
info()  { echo -e "${C_G}[install]${C_0} $*"; }
warn()  { echo -e "${C_Y}[install]${C_0} $*"; }
error() { echo -e "${C_R}[install]${C_0} $*" >&2; }

usage() { grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -16; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --non-interactive|-n) NON_INTERACTIVE=1 ;;
    --llm-url)    LLM_URL="$2"; shift ;;
    --llm-model)  LLM_MODEL="$2"; shift ;;
    --port)       APP_PORT="$2"; shift ;;
    --admin-email)    ADMIN_EMAIL="$2"; shift ;;
    --admin-password) ADMIN_PASSWORD="$2"; shift ;;
    --skip-llm-check) SKIP_LLM_CHECK=1 ;;
    --yes|-y)     ASSUME_YES=1 ;;
    -h|--help)    usage ;;
    *) error "Неизвестный аргумент: $1"; usage ;;
  esac
  shift
done

SUDO=""
if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else
    error "Нужны права root или sudo для установки Docker."
    exit 1
  fi
fi

# ---------------------------------------------------------------- проверка ОС
if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" && "${ID_LIKE:-}" != *"debian"* ]]; then
    warn "ОС '${PRETTY_NAME:-unknown}' не Ubuntu — скрипт рассчитан на Ubuntu 20.04+."
    [[ $ASSUME_YES -eq 1 ]] || { read -r -p "Продолжить? [y/N] " a; [[ "$a" == "y" || "$a" == "Y" ]] || exit 1; }
  fi
fi

rand_hex() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -hex 32
  else od -An -N32 -tx1 /dev/urandom | tr -d ' \n'; fi
}

# ------------------------------------------------------- параметры установки
prompt() { # prompt VAR "вопрос" "значение_по умолчанию"
  local __var="$1" __q="$2" __def="${3:-}" __in
  if [[ $NON_INTERACTIVE -eq 1 ]]; then
    eval "$__var=\"\${$__var:-\$__def}\""; return
  fi
  read -r -p "$(echo -e "${C_B}${__q}${C_0} [${__def}] ")" __in || true
  eval "$__var=\"\${__in:-\${$__var:-\$__def}}\""
}

if [[ $NON_INTERACTIVE -eq 0 ]]; then
  echo -e "${C_B}Установка ITInterview в ${INSTALL_DIR}${C_0}"
fi

# --- ИИ-помощник: OpenAI-совместимый интерфейс (llama.cpp) ------------------
check_llm() { # check_llm URL -> печатает список моделей или ошибку; rc!=0 при недоступности
  local url="${1%/}/models"
  command -v curl >/dev/null 2>&1 || { warn "curl не найден — пропуск проверки LLM"; return 0; }
  local resp
  if ! resp=$(curl -fsS --max-time 8 "$url" 2>/dev/null); then
    return 1
  fi
  MODELS_JSON="$resp"
  return 0
}

while true; do
  prompt LLM_URL "URL OpenAI-совместимого интерфейса ИИ-помощника (llama.cpp)" "$LLM_URL"
  [[ $SKIP_LLM_CHECK -eq 1 ]] && break
  if check_llm "$LLM_URL"; then
    info "LLM доступен: ${LLM_URL}"
    # автоопределение имени модели
    if [[ -z "$LLM_MODEL" ]] && command -v python3 >/dev/null 2>&1; then
      LLM_MODEL=$(echo "${MODELS_JSON:-}" | python3 -c 'import sys,json;d=json.load(sys.stdin);m=d.get("data") or d.get("models") or [];print(m[0].get("id","") if m else "")' 2>/dev/null || true)
    fi
    [[ -n "$LLM_MODEL" ]] && info "Модель определена автоматически: ${LLM_MODEL}"
    break
  fi
  error "Не удалось получить ${LLM_URL%/}/models — ИИ-помощник будет недоступен."
  if [[ $NON_INTERACTIVE -eq 1 ]]; then warn "Продолжаю без проверки (--non-interactive)."; break; fi
  read -r -p "Изменить URL? [y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]] || { warn "LLM будет настроен позже через админку."; break; }
done

prompt APP_PORT        "Порт веб-интерфейса системы" "$APP_PORT"
prompt ADMIN_EMAIL     "Email первого администратора" "$ADMIN_EMAIL"
if [[ -z "$ADMIN_PASSWORD" ]]; then
  if [[ $NON_INTERACTIVE -eq 1 ]]; then ADMIN_PASSWORD=$(rand_hex | head -c 16); warn "Пароль администратора сгенерирован: ${ADMIN_PASSWORD}";
  else prompt ADMIN_PASSWORD "Пароль первого администратора (min 6)" ""; fi
fi

# ------------------------------------------------------------ Docker ---------
COMPOSE=""
detect_compose() {
  if docker compose version >/dev/null 2>&1; then COMPOSE="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then COMPOSE="docker-compose"
  fi
}

if ! command -v docker >/dev/null 2>&1; then
  info "Docker не найден — устанавливаем (get.docker.com)…"
  [[ $ASSUME_YES -eq 1 ]] || { read -r -p "Установить Docker? [Y/n] " a; [[ "$a" =~ ^[nN]$ ]] && exit 1; }
  curl -fsSL https://get.docker.com | $SUDO sh
  $SUDO systemctl enable --now docker || true
else
  info "Docker: $(docker --version)"
fi

detect_compose
if [[ -z "$COMPOSE" ]]; then
  info "docker compose plugin не найден — устанавливаем…"
  $SUDO apt-get update -qq && $SUDO apt-get install -y docker-compose-plugin \
    || { curl -fsSL https://get.docker.com | $SUDO sh; detect_compose; }
fi
[[ -n "$COMPOSE" ]] || { error "Не удалось получить docker compose."; exit 1; }

if ! docker info >/dev/null 2>&1; then
  warn "Нет доступа к докер-демону от текущего пользователя (добавляю в группу docker)."
  $SUDO usermod -aG docker "$USER" || true
  error "Перелогиньтесь (или newgrp docker) и запустите ./install.sh повторно."
  exit 2
fi

# ------------------------------------------------------------- .env ----------
SANDBOX_DIR="$INSTALL_DIR/sandbox-work"
mkdir -p "$SANDBOX_DIR"

if [[ -f .env && $ASSUME_YES -eq 0 && $NON_INTERACTIVE -eq 0 ]]; then
  read -r -p ".env уже существует — перезаписать? [y/N] " a
  if [[ ! "$a" =~ ^[yY]$ ]]; then info "Существующий .env сохранён (параметры LLM можно поправить в админке)."; OVERWRITE_ENV=0; else OVERWRITE_ENV=1; fi
else
  OVERWRITE_ENV=1
fi

if [[ $OVERWRITE_ENV -eq 1 ]]; then
  DB_PASS=$(rand_hex | head -c 24)
  SECRET=$(rand_hex)
  cat > .env <<EOF
# Сгенерировано install.sh $(date -Is)
APP_PORT=${APP_PORT}
SECRET_KEY=${SECRET}

POSTGRES_DB=itrainterview
POSTGRES_USER=itraint
POSTGRES_PASSWORD=${DB_PASS}

LLM_BASE_URL=${LLM_URL}
LLM_MODEL=${LLM_MODEL}
LLM_API_KEY=
LLM_TIMEOUT_SEC=120

SANDBOX_HOST_DIR=${SANDBOX_DIR}
SANDBOX_TIMEOUT_SEC=5
SANDBOX_MEMORY_MB=256

ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
ADMIN_USERNAME=admin

SEED_ON_START=true
CORS_ORIGINS=
EOF
  chmod 600 .env
  info ".env создан (пароль админа: ${ADMIN_PASSWORD})"
fi

# ------------------------------------------------------ сборка и запуск ------
info "Сборка образов-раннеров песочницы (python/node/java/cpp)…"
$COMPOSE --profile runner build

info "Сборка backend и frontend…"
$COMPOSE build

info "Запуск контейнеров…"
$COMPOSE up -d

info "Ожидание готовности (макс. 240 с)…"
ok=0
for i in $(seq 1 120); do
  if curl -fsS --max-time 3 "http://127.0.0.1:${APP_PORT}/api/health" >/dev/null 2>&1; then ok=1; break; fi
  sleep 2
done
[[ $ok -eq 1 ]] || { error "Сервис не поднялся. Смотрите: $COMPOSE logs --tail=100"; exit 3; }

# smoke-тест логина администратора
if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 5 -X POST "http://127.0.0.1:${APP_PORT}/api/auth/login" \
      -H 'Content-Type: application/json' \
      -d "{\"login\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" >/dev/null 2>&1; then
    info "Smoke-тест логина администратора: OK"
  else
    warn "Логин администратора не прошёл smoke-тест — проверьте $COMPOSE logs backend"
  fi
fi

HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}'); HOST_IP="${HOST_IP:-<IP-сервера>}"
echo
echo -e "${C_G}${C_B}Готово!${C_0}"
echo -e "  Интерфейс:        ${C_B}http://${HOST_IP}:${APP_PORT}${C_0}"
echo -e "  Администратор:    ${C_B}${ADMIN_EMAIL}${C_0} / ${ADMIN_PASSWORD}"
echo -e "  ИИ-помощник:      ${LLM_URL} ${LLM_MODEL:+(${LLM_MODEL})}"
echo
echo "Управление: make up | make down | make logs | make build"
echo "Скрипт установки можно запускать повторно — он обновляет образы и перезапускает сервисы."
