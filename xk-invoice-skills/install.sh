#!/usr/bin/env bash
# xk-invoice-skills 一键安装（macOS / Linux）
# 默认安装到 WorkBuddy 用户级技能目录 ~/.workbuddy/skills/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
SKILL_NAMES=(xk-invoice-pipeline xk-pdf-to-jpg xk-invoice-ocr-summary xk-invoice-ledger)

MODE="user"
PROJECT_DIR=""
CUSTOM_DIR=""
FORCE=0
WITH_DEPS=0

usage() {
  cat <<'USAGE'
用法: ./install.sh [选项]

  (无参数)              安装到用户级 ~/.workbuddy/skills/
  --user                同上（显式写法）
  --project <项目目录>   安装到 <项目目录>/.workbuddy/skills/
  --dir <目录>          安装到任意指定目录（用于测试 / 其他 Agent）
  --force               已存在同名技能时覆盖（原目录自动移到备份，不删除）
  --with-deps           同时用 pip 安装 PyMuPDF / openpyxl
  -h, --help            显示帮助

示例:
  ./install.sh
  ./install.sh --project ~/code/my-project
  ./install.sh --dir /tmp/skill-test --force --with-deps
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user) MODE="user"; shift ;;
    --project)
      if [[ $# -lt 2 ]]; then echo "✗ --project 缺少目录参数" >&2; exit 1; fi
      MODE="project"; PROJECT_DIR="$2"; shift 2 ;;
    --dir)
      if [[ $# -lt 2 ]]; then echo "✗ --dir 缺少目录参数" >&2; exit 1; fi
      MODE="custom"; CUSTOM_DIR="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --with-deps) WITH_DEPS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "✗ 未知参数: $1" >&2; usage; exit 1 ;;
  esac
done

case "$MODE" in
  user)    TARGET="$HOME/.workbuddy/skills" ;;
  project) TARGET="$PROJECT_DIR/.workbuddy/skills" ;;
  custom)  TARGET="$CUSTOM_DIR" ;;
esac

if [[ ! -d "$SKILLS_SRC" ]]; then
  echo "✗ 找不到 skills/ 目录，请在仓库根目录运行本脚本" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "⚠ 未检测到 python3：技能文件仍会安装，但运行前请先装 Python 3.9+"
fi

mkdir -p "$TARGET"
echo "安装目标: $TARGET"
echo

BACKUP=""
INSTALLED=0
SKIPPED=0

for name in "${SKILL_NAMES[@]}"; do
  if [[ -d "$TARGET/$name" ]]; then
    if [[ $FORCE -eq 0 ]]; then
      echo "  跳过  ${name} （已存在；如需覆盖加 --force）"
      SKIPPED=$((SKIPPED + 1))
      continue
    fi
    if [[ -z "$BACKUP" ]]; then
      BACKUP="$(dirname "$TARGET")/skills_backup_$(date +%Y%m%d_%H%M%S)"
      mkdir -p "$BACKUP"
    fi
    # 用「移动」而不是删除：旧版本可随时找回
    mv "$TARGET/$name" "$BACKUP/$name"
  fi
  cp -R "$SKILLS_SRC/$name" "$TARGET/$name"
  echo "  ✓ 安装  $name"
  INSTALLED=$((INSTALLED + 1))
done

echo
echo "完成：新装 $INSTALLED 个，跳过 $SKIPPED 个"
[[ -n "$BACKUP" ]] && echo "原版本备份: $BACKUP"

if [[ $WITH_DEPS -eq 1 ]]; then
  echo
  echo "安装 Python 依赖…"
  python3 -m pip install -r "$REPO_ROOT/requirements.txt"
fi

echo
echo "下一步："
echo "  1) 环境自检  python3 \"$REPO_ROOT/scripts/check_env.py\" --skills-dir \"$TARGET\""
echo "  2) 未装依赖时手动执行  python3 -m pip install -r \"$REPO_ROOT/requirements.txt\""
echo "  3) 重启 WorkBuddy（或重新加载技能），对助手说：处理 <发票目录> 的发票出报销台账"
