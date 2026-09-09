#!/usr/bin/env bash
# install-ref-override-test — cổng nghiệm thu KHÔNG được mù với chính bản đang nghiệm thu.
#
# Bất-biến: nguồn clone của install-harness.sh phải ĐI THEO ref mà người cài đang trỏ tới.
# Trước rào này, 4 lệnh clone đều hardcode `-b orca`: UAT canary override REPO_RAW/SKILLS_REF
# vẫn bị kéo hook+engine từ nhánh CHÍNH → canary chấm bản CŨ rồi báo kết quả cho bản MỚI.
# Mù với: llmwiki/.claude/hooks/**, harness/scripts/**, harness/validators/**, fdk/tools/**.
# Đã cháy thật 2026-07-17 (UAT auto-capture: hook global 2121B, record_bite=0 dù canary có).
#
# Usage: bash harness/tests/install-ref-override-test.sh [repo-root]   (exit 0 = pass)
set -u
ROOT="$(cd "${1:-.}" && pwd)"
IH="$ROOT/harness/scripts/install-harness.sh"
fail=0
ok()  { printf '  \033[1;32m✓\033[0m %s\n' "$1"; }
bad() { printf '  \033[1;31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

ref() { env -u HARNESS_REF -u REPO_RAW "$@" bash "$IH" --print-ref 2>/dev/null; }

# Nhánh mặc định KHÔNG hardcode trong test: repo gốc mặc định `orca`, fork mặc định nhánh của
# chính nó (`main`). Ghim tên nhánh ở đây thì mọi fork đều đỏ vì một lý do không liên quan gì
# tới bất-biến đang gác. Lấy đúng giá trị fallback mà install-harness.sh tự khai.
DEF_REF=$(sed -nE 's/^HARNESS_REF="\$\{HARNESS_REF:-([^}]*)\}".*/\1/p' "$IH" | tail -1)
DEF_REPO=$(sed -nE 's/^HARNESS_REPO="\$\{HARNESS_REPO:-([^}]*)\}".*/\1/p' "$IH" | tail -1)
[ -n "$DEF_REF" ] || { printf '  \033[1;31m✗\033[0m không đọc được fallback HARNESS_REF trong %s\n' "$IH"; exit 1; }

# 1. Không ai trỏ gì → đúng nhánh mặc định script tự khai (người cài bình thường không đổi hành vi).
r=$(ref); [ "$r" = "$DEF_REF" ] && ok "mặc định = $DEF_REF (người cài bình thường không đổi)" \
                            || bad "mặc định phải là $DEF_REF, ra '$r'"

# 2. REPO_RAW trỏ canary → ref ĐI THEO canary. Đây là ca đã cháy.
r=$(ref REPO_RAW="https://raw.githubusercontent.com/Rheinmir/setup/uat/260717-2105")
[ "$r" = "uat/260717-2105" ] && ok "REPO_RAW canary → ref đi theo (giữ nguyên ref có dấu /)" \
                             || bad "canary ref sai: kỳ vọng 'uat/260717-2105', ra '$r'"

# 3. HARNESS_REF ép tay thắng suy diễn.
r=$(env HARNESS_REF=my-branch bash "$IH" --print-ref 2>/dev/null)
[ "$r" = "my-branch" ] && ok "HARNESS_REF ép tay thắng REPO_RAW" \
                       || bad "HARNESS_REF phải thắng, ra '$r'"

# 4. REPO_RAW lạ host (không phải raw.githubusercontent) → không đoán bừa, về mặc định.
r=$(ref REPO_RAW="https://example.com/whatever")
[ "$r" = "$DEF_REF" ] && ok "REPO_RAW lạ host → không đoán bừa, về $DEF_REF" \
                  || bad "host lạ phải fallback $DEF_REF, ra '$r'"

# 5. Rào chống tái phát: không còn lệnh clone nào ghim cứng tên nhánh.
n=$(grep -cE '^[^#]*git clone .*-b +(orca|main|master)\b' "$IH" 2>/dev/null || true)
[ "${n:-0}" -eq 0 ] && ok "không còn clone hardcode tên nhánh trong install-harness.sh" \
                    || bad "$n lệnh clone còn ghim cứng tên nhánh → canary sẽ lại chấm nhầm bản"

# 6. Định danh nguồn phải KHỚP giữa hai file cài. Đây là chỗ fork hay retarget một file rồi
# quên file kia: install.sh kéo nội dung từ repo A còn install-harness.sh clone engine từ repo B
# → người mới cài được nửa bản này nửa bản kia mà không có lỗi nào nổi lên.
IS="$ROOT/harness/poc-vendor-neutral/install.sh"
raw=$(sed -nE 's#.*REPO_RAW:-https://raw\.githubusercontent\.com/([^}"]+)\}.*#\1#p' "$IS" | tail -1)
if [ -z "$raw" ]; then
  bad "không đọc được REPO_RAW mặc định trong install.sh"
else
  raw_repo=$(printf '%s' "$raw" | cut -d/ -f1-2)
  raw_ref=$(printf '%s' "$raw" | cut -d/ -f3-)
  if [ "$raw_repo" = "$DEF_REPO" ] && [ "$raw_ref" = "$DEF_REF" ]; then
    ok "install.sh và install-harness.sh cùng trỏ $DEF_REPO@$DEF_REF"
  else
    bad "lệch nguồn: install.sh → $raw_repo@$raw_ref, install-harness.sh → $DEF_REPO@$DEF_REF"
  fi
fi

if [ "$fail" -eq 0 ]; then
  printf '\n\033[1m═══ install-ref-override: \033[1;32mPASS\033[0m\033[0m\n'; exit 0
fi
printf '\n\033[1m═══ install-ref-override: \033[1;31m%d VI PHẠM\033[0m\033[0m\n' "$fail"; exit 1
