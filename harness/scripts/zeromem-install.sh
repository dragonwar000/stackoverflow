#!/usr/bin/env bash
# zeromem-install — cài zm đúng revision đã ghim và tải model bge-small, kiểm sha256 trước khi nhận.
#   zeromem-install.sh                    cài zm + tải model vào thư mục chung, rồi kiểm sha
#   zeromem-install.sh --verify-only DIR  chỉ kiểm sha các file model trong DIR
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LOCK="${ZEROMEM_LOCK:-$HERE/../zeromem/zeromem-lock.json}"
SHARED="${OVERSTACK_ZEROMEM_SHARED:-$HOME/.overstack/zeromem/_shared}"

verify_dir() {  # $1 = thư mục chứa các file model theo đường dẫn tương đối trong lock
  python3 - "$LOCK" "$1" <<'PY'
import hashlib, json, os, sys
lock = json.load(open(sys.argv[1], encoding="utf-8"))
base = sys.argv[2]
files = lock["model"]["files"]
bad = 0
for rel, want in files.items():
    p = os.path.join(base, rel)
    if not os.path.isfile(p):
        print(f"THIẾU {rel}")
        bad += 1
        continue
    got = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if got != want:
        print(f"LỆCH {rel}")
        bad += 1
print(f"{len(files) - bad}/{len(files)} file khớp sha256")
sys.exit(1 if bad else 0)
PY
}

if [ "${1:-}" = "--verify-only" ]; then
  verify_dir "${2:?thiếu DIR}"; exit $?
fi

REPO=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['repository'])" "$LOCK")
REV=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['rev'])" "$LOCK")
MODEL_REPO=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['model']['repository'])" "$LOCK")
MODEL_REV=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['model']['rev'])" "$LOCK")

command -v cargo >/dev/null 2>&1 || { echo "thiếu cargo — cài rustup trước"; exit 2; }
cargo install --git "$REPO" --rev "$REV" --locked zeromem || { echo "cargo install zeromem thất bại"; exit 1; }
command -v zm >/dev/null 2>&1 || { echo "zm không có trong PATH sau khi cài"; exit 1; }

mkdir -p "$SHARED" && chmod 700 "$SHARED"
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"zeromem-install","version":"1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"zeromem_recall","arguments":{"query":"warm","top_k":1}}}' \
  | zm mcp --home "$SHARED" >/dev/null 2>&1 || echo "cảnh báo: lượt khởi động model trả lỗi, sẽ kiểm sha để xác định"
rm -f "$SHARED"/zeromem.db "$SHARED"/zeromem.db-*

SNAP="$SHARED/models/models--${MODEL_REPO//\//--}/snapshots/$MODEL_REV"
if verify_dir "$SNAP"; then
  echo "zeromem sẵn sàng: $(command -v zm), model tại $SNAP"
  exit 0
fi
if [ -d "$SNAP" ]; then
  mkdir -p "$SHARED/models/rejected"
  mv "$SNAP" "$SHARED/models/rejected/$(date +%Y%m%d%H%M%S)"
  echo "model bị từ chối: sha không khớp lock, đã chuyển vào models/rejected"
else
  echo "model bị từ chối: thiếu snapshot $SNAP"
fi
exit 1
