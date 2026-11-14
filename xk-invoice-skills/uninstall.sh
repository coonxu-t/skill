#!/usr/bin/env bash
# 卸载 xk-invoice-skills（macOS / Linux）
# 默认只预览；加 --yes 才执行。执行方式是「移动到备份目录」，不做删除，随时可恢复。
set -euo pipefail

SKILL_NAMES=(xk-invoice-pipeline xk-pdf-to-jpg xk-invoice-ocr-summary xk-invoice-ledger)
APPLY=0
TARGET="$HOME/.workbuddy/skills"

usage() {
  cat <<'USAGE'
用法: ./uninstall.sh [选项]

  (无参数)        预览将被卸载的技能（不改动任何文件）
  --yes           真正执行卸载（移动到备份目录）
  --dir <目录>     指定技能所在目录（默认 ~/.workbuddy/skills）
  -h, --help      显示帮助
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) APPLY=1; shift ;;
    --dir)
      if [[ $# -lt 2 ]]; then echo "✗ --dir 缺少目录参数" >&2; exit 1; fi
      TARGET="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "✗ 未知参数: $1" >&2; usage; exit 1 ;;
  esac
done

FOUND=()
for name in "${SKILL_NAMES[@]}"; do
  [[ -d "$TARGET/$name" ]] && FOUND+=("$name")
done

echo "技能目录: $TARGET"
if [[ ${#FOUND[@]} -eq 0 ]]; then
  echo "没有找到本套技能，无需卸载。"
  exit 0
fi

echo "将卸载 ${#FOUND[@]} 个技能："
for name in "${FOUND[@]}"; do echo "  - $TARGET/$name"; done

if [[ $APPLY -eq 0 ]]; then
  echo
  echo "这是预览模式，未改动任何文件。确认后加 --yes 执行。"
  exit 0
fi

BACKUP="$(dirname "$TARGET")/skills_uninstalled_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP"
for name in "${FOUND[@]}"; do
  mv "$TARGET/$name" "$BACKUP/$name"
  echo "  ✓ 已移出  $name"
done
echo
echo "卸载完成。原文件保存在: $BACKUP"
echo "如需恢复，把里面的目录移回 $TARGET 即可。"
