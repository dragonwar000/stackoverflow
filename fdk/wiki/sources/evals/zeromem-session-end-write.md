---
type: eval
id: zeromem-session-end-write
title: "session_end.py ghi zeromem bằng subprocess.run, không dùng _run của Stop"
input: "Trong llmwiki/.claude/hooks, stop.py ghi turn vào zeromem bằng _run(...). Vì sao session_end.py có một bản zeromem_write riêng dùng subprocess.run thay vì gọi _run hoặc import hàm từ stop.py?"
expected: "_run là hàm của stop.py, kẹp timeout theo ngân sách Stop (OVERSTACK_STOP_BUDGET_S, mặc định 20 giây). session_end.py không có _run và không có ngân sách đó; nếu chép nguyên bản dùng _run thì gặp NameError, bị except nuốt, và nhánh SessionEnd chết im lặng. Vì vậy session_end.py giữ một bản sao dùng subprocess.run với timeout 12 giây trong try/except, import resolve_tool cục bộ, và không import chéo giữa các hook."
asserts:
  - 'icontains:subprocess'
  - 'icontains:_run'
  - 'regex:(?i)(ngân sách|budget)'
  - 'regex:(?i)(NameError|không có _run|không định nghĩa|chưa định nghĩa|không tồn tại)'
rubric: "ĐẠT nếu nêu được _run gắn với ngân sách Stop và session_end.py không có hàm đó. KHÔNG đạt nếu chỉ nói 'cho gọn' hay 'tránh trùng lặp'."
---

# Golden: zeromem-session-end-write

Hỏi lại chỗ PLAN zeromem lệch code ở Task 4 (commit `ebada577`). Hành vi khoá bằng `harness/tests/zeromem-hooks-test.sh` (ca SessionEnd không Traceback).

## Origin
- Phiên coordinator 03/10/2026, branch `merge/setup-031026`. PLAN: `llmwiki/wiki/sources/draft/031026-zeromem-parallel-backend-PLAN.md`.
