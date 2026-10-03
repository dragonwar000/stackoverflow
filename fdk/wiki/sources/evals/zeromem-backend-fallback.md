---
type: eval
id: zeromem-backend-fallback
title: "memory.backend mặc định zeromem, thiếu zm thì rơi về mem-rank"
input: "Khoá memory.backend của harness có mặc định là gì, khai ở đâu, và chuyện gì xảy ra khi máy không cài zm?"
expected: "Mặc định là zeromem, khai ở khoá memory.backend trong harness/mem-rank.config.yaml; thiếu khoá cũng coi là zeromem. Giá trị hợp lệ là zeromem, mem-rank, both; giá trị lạ trả invalid và hook giữ mem-rank. Khi backend là zeromem mà máy không có zm, zeromem-bridge.py rơi về mem-rank (fail-open), nên phiên làm việc không bị chặn và chuỗi mem-rank vẫn chạy."
asserts:
  - 'icontains:zeromem'
  - 'icontains:mem-rank'
  - 'icontains:mem-rank.config.yaml'
  - 'regex:(?i)(rơi về|fallback|fall back|fail-open về|quay về|lùi về|tạm dùng|hạ cấp)'
rubric: "ĐẠT nếu nêu đúng mặc định, đúng file config, và hành vi rơi về mem-rank khi thiếu zm. KHÔNG đạt nếu nói thiếu zm thì lỗi hoặc chặn phiên."
---

# Golden: zeromem-backend-fallback

Hỏi lại Task 3 của PLAN zeromem (commit `a22ac262`). Hành vi khoá bằng `harness/tests/zeromem-bridge-test.sh` (ca backend và ca thiếu zm).

## Origin
- Phiên coordinator 03/10/2026, branch `merge/setup-031026`. PLAN: `llmwiki/wiki/sources/draft/031026-zeromem-parallel-backend-PLAN.md`.
