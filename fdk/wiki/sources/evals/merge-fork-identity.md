---
type: eval
id: merge-fork-identity
title: "Merge upstream vào fork — tách cải tiến CẤU TRÚC khỏi dòng ĐỊNH DANH trong cùng một hunk"
input: "Một fork đã đổi nguồn cài trỏ về chính nó. Kéo upstream về thì xung đột rơi đúng dòng REPO_RAW trong install.sh. Giải xung đột đó thế nào, và nghiệm thu bằng gì để chắc merge không kéo ngược định danh về repo gốc?"
expected: "Tách hai thứ đang chồng lên nhau trong cùng một hunk: cải tiến CẤU TRÚC của upstream (biến $OVERSTACK_DIR thay đường dẫn cứng) thì lấy, còn dòng ĐỊNH DANH (REPO_RAW, SKILLS_REF, HARNESS_REPO) thì giữ của fork — không bên nào đúng toàn phần nên lấy ours/theirs cho cả file đều sai. Nghiệm thu hai lớp: grep lại toàn bộ đường cài (README, bootstrap.sh, bootstrap-fork.sh, install.sh, install-harness.sh) xem còn trỏ fork không; rồi diff cây đã merge với upstream — phần chênh còn lại phải đúng bằng tập file định danh đã liệt kê trước, dư một file nghĩa là merge kéo ngược, thiếu một file nghĩa là mất phần riêng của fork."
asserts:
  - 'contains:REPO_RAW'
  - 'icontains:định danh'
  - 'regex:(?i)ours/theirs'
  - 'regex:(?i)(grep|diff)'
rubric: "ĐẠT nếu nêu được: (1) trong một hunk có thể trộn cải tiến cấu trúc (lấy) với dòng định danh (giữ), nên ours/theirs cả file là sai; (2) nghiệm thu bằng grep đường cài CỘNG diff cây merge với upstream, và biết đọc kết quả diff theo cả hai chiều dư/thiếu. KHÔNG đạt nếu chỉ nói chung chung 'giải xung đột cẩn thận' hoặc chỉ nêu một lớp nghiệm thu."
---

# Golden: merge-fork-identity

Rút từ đợt merge thật 2026-09-08 — kéo 106 commit `Rheinmir/setup@orca` vào fork
`dragonwar000/stackoverflow@main` sau 40 ngày rẽ nhánh.

Xung đột duy nhất trong `install.sh` gói đúng bốn dòng, và hai bên sửa **hai chuyện khác
nhau** trên cùng chỗ đó: upstream thay đường dẫn cứng bằng biến `$OVERSTACK_DIR`; fork
đổi `REPO_RAW` từ `Rheinmir/setup/orca` sang `dragonwar000/stackoverflow/main`. Lấy
`--theirs` thì mất nguồn cài của fork (người mới `curl` về sẽ cài bản upstream); lấy
`--ours` thì mất cải tiến layout. Cả hai lựa chọn mặc định đều **im lặng** — không lỗi,
không cảnh báo, chỉ sai.

Lớp nghiệm thu thứ hai mới là lớp bắt được sai sót: sau merge, `git diff HEAD origin/orca`
phải trả về đúng tập file định danh đã liệt kê **trước khi** merge (ở đây: 5 file cài + 2
bản `orca-onboard`). Con số khớp là bằng chứng hai chiều — không kéo ngược thứ gì của
upstream, cũng không đánh rơi thứ gì của fork.

## Origin
- Distill từ phiên merge 2026-09-08 (`e493ac29`) — golden neo bài học "ours/theirs cả file
  là chỗ đánh mất định danh fork âm thầm" vào eval hồi quy. Ghi chép đầy đủ:
  `llmwiki/wiki/draft/cave/080926-merge-upstream-setup.md`.
