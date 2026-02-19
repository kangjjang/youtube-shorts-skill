#!/bin/bash
# YouTube Shorts 스킬 의존성 자동 설치
set -e

SKILL_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

# Python venv + 의존성
if [ ! -d "$SKILL_DIR/.venv" ]; then
  echo "[youtube-shorts] Python venv 생성 중..."
  python3 -m venv "$SKILL_DIR/.venv"
fi

if [ ! -f "$SKILL_DIR/.venv/.installed" ]; then
  echo "[youtube-shorts] Python 의존성 설치 중..."
  "$SKILL_DIR/.venv/bin/pip" install -q -r "$SKILL_DIR/requirements.txt"
  touch "$SKILL_DIR/.venv/.installed"
fi

# Remotion (Node.js)
if [ -d "$SKILL_DIR/remotion" ] && [ ! -d "$SKILL_DIR/remotion/node_modules" ]; then
  if command -v npm &> /dev/null; then
    echo "[youtube-shorts] Remotion 의존성 설치 중..."
    cd "$SKILL_DIR/remotion" && npm install --silent
  else
    echo "[youtube-shorts] npm이 없습니다. Remotion 합성을 위해 Node.js를 설치하세요."
  fi
fi

echo "[youtube-shorts] 준비 완료."
