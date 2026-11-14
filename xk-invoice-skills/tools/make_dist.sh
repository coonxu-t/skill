#!/usr/bin/env bash
# 重新生成分发包：dist/xk-invoice-skills.zip / .tar.gz / SHA256SUMS.txt
# 用法: ./tools/make_dist.sh [版本号，可选，只影响打印]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "$REPO_ROOT")"
PARENT="$(dirname "$REPO_ROOT")"
OUT="$REPO_ROOT/dist"
VERSION="${1:-dev}"

mkdir -p "$OUT"
cd "$PARENT"

rm -f "$OUT/$NAME.zip" "$OUT/$NAME.tar.gz" "$OUT/SHA256SUMS.txt"

# 用 Python 打包，而不是系统 zip：
# macOS 自带 zip 不写 UTF-8 文件名标志，中文文件名到 Windows/别的电脑会解压成乱码。
# zipfile 会自动置 UTF-8 flag(bit 11)，tarfile 用 PAX 格式保存 UTF-8 名称。
python3 - "$REPO_ROOT" "$OUT/$NAME.zip" "$OUT/$NAME.tar.gz" <<'PY'
import os
import sys
import tarfile
import time
import zipfile

repo, zpath, tpath = sys.argv[1], sys.argv[2], sys.argv[3]
os.chdir(os.path.dirname(repo))
root = os.path.basename(repo)

EXCLUDE_DIRS = {
    ".git", "dist", "__pycache__", ".venv", ".pytest_cache",
    ".idea", ".vscode", "invoice", "tu",
}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", "发票数据.json"}


def skip_dir(d):
    return d in EXCLUDE_DIRS or d.startswith(("skills_backup_", "skills_uninstalled_"))


def skip_file(f):
    return f in EXCLUDE_FILES or f.endswith(
        (".pyc", ".pyo", ".xlsx", ".xls", ".swp", "_small.jpg")
    )


files = []
for cur, dirs, names in os.walk(root):
    dirs[:] = sorted(d for d in dirs if not skip_dir(d))
    for f in sorted(names):
        if not skip_file(f):
            files.append(os.path.join(cur, f))

with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for p in files:
        st = os.stat(p)
        zi = zipfile.ZipInfo(p, date_time=time.localtime(st.st_mtime)[:6])
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.create_system = 3  # Unix，external_attr 里的权限位才生效
        zi.external_attr = st.st_mode << 16
        with open(p, "rb") as fh:
            z.writestr(zi, fh.read())

with tarfile.open(tpath, "w:gz", format=tarfile.PAX_FORMAT) as t:
    for p in files:
        t.add(p, arcname=p, recursive=False)

print(f"打包文件数: {len(files)}")
PY

cd "$OUT"
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$NAME.zip" "$NAME.tar.gz" > SHA256SUMS.txt
else
  sha256sum "$NAME.zip" "$NAME.tar.gz" > SHA256SUMS.txt
fi

echo "版本标签: $VERSION"
echo "分发包已生成于: $OUT"
ls -lh "$NAME.zip" "$NAME.tar.gz" SHA256SUMS.txt
echo
echo "zip 内文件数: $(unzip -Z1 "$NAME.zip" | wc -l | tr -d ' ')"
echo "SHA256:"
cat SHA256SUMS.txt
