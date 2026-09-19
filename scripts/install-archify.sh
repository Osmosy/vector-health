#!/usr/bin/env bash
# Установка archify для проверки диаграммы в CI.
#
# Почему так, а не `npm install`:
#   - пакет скилла помечен `private: true` и в npm не публикуется, одноимённый
#     `archify` в реестре — другой проект (0.0.4), ставить его нельзя;
#   - у самого скилла НЕТ runtime-зависимостей (`dependencies` в его
#     package.json пуст), поэтому достаточно исходников: node_modules не нужен;
#   - в архиве репозитория пакет лежит НЕ в корне, а в подкаталоге `archify/` —
#     распаковка в корень даёт «bin/archify.mjs: No such file».

set -euo pipefail

VERSION="${ARCHIFY_VERSION:-v2.16.0}"
DEST="${1:-archify}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "archify: ставлю ${VERSION} в ${DEST}"
curl -fsSL -o "$TMP/a.tgz" \
  "https://codeload.github.com/tt-a1i/archify/tar.gz/refs/tags/${VERSION}"

# --strip-components=1 убирает «archify-<version>/», остаётся дерево репозитория,
# внутри которого пакет скилла — в подкаталоге archify/
tar -xzf "$TMP/a.tgz" -C "$TMP" --strip-components=1

if [ ! -f "$TMP/archify/bin/archify.mjs" ]; then
  echo "ОШИБКА: в архиве ${VERSION} нет archify/bin/archify.mjs — проверь раскладку пакета" >&2
  echo "содержимое архива:" >&2
  ls "$TMP" >&2
  exit 1
fi

rm -rf "$DEST"
mv "$TMP/archify" "$DEST"

# Установка обязана доказать свою работоспособность: doctor проверяет шаблоны,
# рендерер и рантаймы. Молчаливо неработающая установка выглядела бы как
# «проверка диаграммы прошла».
node "$DEST/bin/archify.mjs" doctor

echo "archify: ok ($(node -e "console.log(require('./$DEST/package.json').version)" 2>/dev/null || echo "$VERSION"))"
