#!/usr/bin/env bash
# Финальная приёмка vector-health: весь контур проверок, как в CI плюс офлайн-изоляция.
#
# Запуск: bash scripts/acceptance.sh
#
# Зачем отдельный скрипт: приёмка из плана внешнего аудита — это семь команд плюс
# прогон в окружении без сети. Собранные в один файл, они выполняются одной
# командой и не забываются по частям; в логе видно, какой шаг упал.
set -u
cd "$(dirname "$0")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
FAILED=0
step() {
  local name="$1"; shift
  printf '\n=== %s ===\n' "$name"
  if "$@"; then
    printf 'ok: %s\n' "$name"
  else
    printf 'ПРОВАЛ: %s\n' "$name"
    FAILED=$((FAILED + 1))
  fi
}

step "валидатор (числа, лицензии, ссылки, структура NOTICE, испытания)" \
  python3 -B scripts/validate.py
step "числа в документах из stats.json" \
  python3 -B scripts/sync_doc_numbers.py --check
step "у собственных навыков битых ссылок нет" \
  python3 -B scripts/broken_refs.py --strict-own --no-report
step "тесты со сверкой апстримов по сети" \
  python3 -B tests/test_scripts.py --network
step "мутационные проверки (каждая мутация обязана ронять проверку)" \
  python3 -B tests/mutation_check.py
step "каталог навыков воспроизводится" bash -c \
  'python3 -B scripts/build_index.py && git diff --exit-code --quiet skills-index.json'
step "stats.json воспроизводится" bash -c \
  'python3 -B scripts/build_stats.py --check'
step "docs/for-review.md воспроизводится" \
  python3 -B scripts/build_for_review.py --check

# Без сети целиком. bwrap есть не везде; docker — запасной вариант.
printf '\n=== тесты в окружении без сети ===\n'
if command -v bwrap >/dev/null 2>&1; then
  bwrap --bind / / --dev /dev --proc /proc --unshare-net --chdir "$PWD" \
    env PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_offline.py \
    || { printf 'ПРОВАЛ: тесты без сети (bwrap)\n'; FAILED=$((FAILED + 1)); }
  bwrap --bind / / --dev /dev --proc /proc --unshare-net --chdir "$PWD" \
    env PYTHONDONTWRITEBYTECODE=1 VH_OFFLINE=1 \
    python3 -B scripts/broken_refs.py --strict-own --no-report \
    || { printf 'ПРОВАЛ: --strict-own без сети (bwrap)\n'; FAILED=$((FAILED + 1)); }
elif command -v docker >/dev/null 2>&1; then
  docker run --rm --network none -v "$PWD":/w -w /w python:3.12 \
    python3 -B tests/run_offline.py \
    || { printf 'ПРОВАЛ: тесты без сети (docker)\n'; FAILED=$((FAILED + 1)); }
else
  printf 'нет bwrap и docker — прогон без сети не выполнен (это не «пройдено»)\n'
  FAILED=$((FAILED + 1))
fi

printf '\n===== ИТОГ: провалов %d =====\n' "$FAILED"
[ "$FAILED" -eq 0 ] || exit 1
