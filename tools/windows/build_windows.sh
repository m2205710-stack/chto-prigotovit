#!/usr/bin/env bash
# Собирает готовую папку приложения для Windows (Python встроен, ставить ничего не нужно).
# Работает на Linux: Python для Windows берётся из conda-forge, PySide6 — из PyPI,
# файлы запуска собираются компилятором MinGW.
#
#   bash tools/windows/build_windows.sh <рабочая папка> <папка результата>
set -euo pipefail
APP="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$1"; OUT="$2"
NAME="Что приготовить"
mkdir -p "$WORK"; cd "$WORK"

# 1. Python 3.12 для Windows из conda-forge (через micromamba)
if [ ! -x mm/bin/micromamba ]; then
  curl -sSfL -o mm.tar.bz2 https://conda.anaconda.org/conda-forge/linux-64/micromamba-2.10.0-0.tar.bz2
  mkdir -p mm && tar xjf mm.tar.bz2 -C mm
fi
if [ ! -f pyenv/python.exe ]; then
  MAMBA_ROOT_PREFIX="$WORK/mroot" ./mm/bin/micromamba create -y -q -p "$WORK/pyenv" \
    --platform win-64 -c conda-forge --override-channels "python=3.12"
  # 2. PySide6 для Windows
  pip install -q --break-system-packages --platform win_amd64 --python-version 3.12 --implementation cp \
    --only-binary=:all: --target "$WORK/pyenv/Lib/site-packages" "PySide6-Essentials==6.12.0"
  # 3. убираем всё, что приложению не нужно
  python3 "$APP/tools/windows/prune.py" "$WORK/pyenv"
fi

# 4. файлы запуска со значком
x86_64-w64-mingw32-windres "$APP/tools/windows/app.rc" -O coff -o res.o
x86_64-w64-mingw32-gcc -municode -O2 -s "$APP/tools/windows/launcher.c" res.o -o launcher.exe -mwindows
x86_64-w64-mingw32-gcc -municode -O2 -s -DCONSOLE_SCRIPT='L"tests\\test_tz.py"' "$APP/tools/windows/launcher.c" res.o -o tests.exe

# 5. сборка папки
python3 "$APP/tools/build_db.py"
rm -rf "$OUT"; mkdir -p "$OUT/$NAME"
D="$OUT/$NAME"
cp -r pyenv "$D/runtime"
mkdir -p "$D/app"
( cd "$APP" && cp -r main.py core ui data tools tests requirements.txt README.md "$D/app/" )
mkdir -p "$D/app/assets"
( cd "$APP/assets" && cp -r cookbook.db icons dish_art fonts app.ico app_icon.png "$D/app/assets/" )
find "$D/app" -name __pycache__ -type d -prune -exec rm -rf {} +
cp launcher.exe "$D/$NAME.exe"
cp tests.exe "$D/Проверка ТЗ.exe"
cp "$APP/tools/windows/Прочитай меня.txt" "$D/"
echo "Готово: $D"
