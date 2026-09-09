---
type: eval
id: merge-superset-conflict
title: "Xung đột khi hai nhánh cùng vá một bug — đo quan hệ hai bản trước, chọn sau"
input: "Hai nhánh cùng vá một bug trên cùng một file, đến lúc merge thì xung đột. Chọn bên nào, và lấy gì làm bằng chứng cho lựa chọn đó?"
expected: "Đo trước, chọn sau: diff hai bản với nhau chứ đừng nhìn hai nửa của hunk. Nếu một bên là SUPERSET — chứa đúng cái fix của bên kia cộng thêm phần mới — thì lấy trọn bên đó, và phải nói ra được vì sao không mất gì. Nếu không bên nào bao bên nào thì hợp nhất tay. Ví dụ thật: egress-guard.py, bản fork gắn domain với lệnh net thật, bản upstream có đúng phần đó cộng lớp lọc _NOT_A_TLD/bare_ok chống báo oan đuôi file và thuộc tính code — lấy upstream, mất 0 dòng, và diff với bản upstream sau đó xác nhận file khớp nguyên văn. Mặc định ours/theirs khi chưa đo chính là chỗ đánh mất một fix âm thầm."
asserts:
  - 'icontains:superset'
  - 'contains:egress-guard'
  - 'regex:(?i)(đo trước|diff)'
  - 'regex:(?i)(không mất|mất 0)'
rubric: "ĐẠT nếu nêu được: (1) đo quan hệ hai bản bằng diff TRƯỚC khi chọn, (2) khái niệm superset và điều kiện lấy trọn một bên, (3) nếu không bao nhau thì hợp nhất tay, (4) bằng chứng 'không mất gì' phải nói ra được. KHÔNG đạt nếu chọn theo cảm tính upstream-luôn-mới hoặc fork-luôn-đúng."
---

# Golden: merge-superset-conflict

Rút từ đợt merge thật 2026-09-08. `harness/scripts/egress-guard.py` xung đột vì **cả hai
bên đều vá cùng một bug**: guard chấm host trong toàn bộ command string nên chặn nhầm cả
commit message.

Fork vá bằng `be3d679` (thu phạm vi về đúng segment có lệnh net). Upstream vá cùng chuyện
đó, rồi đi tiếp một bước — thêm `_NOT_A_TLD` và cờ `bare_ok` để `bootstrap.sh`, `uat.env`,
`spec.loader` không bị đọc thành hostname (đo 2026-09-04: một lệnh UAT hợp lệ bị chặn vì
`spec.loader`).

Cách quyết: `git show` cả hai bản ra file rồi `diff` **hai bản với nhau** — không phải đọc
hai nửa của conflict hunk, vì hunk chỉ cho thấy chỗ chạm nhau chứ không cho thấy quan hệ
bao hàm. Diff cho ra quan hệ superset → lấy upstream, và câu "mất 0 dòng" là kết luận đo
được chứ không phải phỏng đoán.

## Origin
- Distill từ phiên merge 2026-09-08 (`e493ac29`) — golden neo bài học "đo quan hệ hai bản
  trước khi chọn bên" vào eval hồi quy. Ghi chép đầy đủ:
  `llmwiki/wiki/draft/cave/080926-merge-upstream-setup.md`.
