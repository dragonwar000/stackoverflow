---
type: eval
id: feature-switch-wikigraph-memory
title: "Tắt wikigraph tắt vẽ graph và lời nhắc, không tắt bộ nhớ thứ cấp"
input: "Dự án đã có .harness-stamp. Tôi đặt OVERSTACK_WIKIGRAPH=0. Ở hook Stop, wiki-graph có còn được vẽ không, và bộ nhớ thứ cấp (scratch-log, provenance, memory-map, episode) có còn chạy không?"
expected: "Wiki-graph không còn được vẽ: regen_docs trong stop.py gọi feature_enabled(root, 'wikigraph', default=(is_framework or has_stamp)), và env cũ OVERSTACK_WIKIGRAPH=0 là legacy_off nên thắng mặc định theo stamp; hook in một dòng stderr nêu nguồn tắt. Lời nhắc ở SessionStart cũng im. Bộ nhớ thứ cấp vẫn chạy: secondary_memory gác bằng is_framework or has_stamp or feature_on(...), tức stamp là đủ, công tắc wikigraph chỉ là opt-in cho dự án chưa stamp."
asserts:
  - 'icontains:stamp'
  - 'regex:(?i)(không còn (được )?vẽ|không vẽ|ngừng vẽ|tắt (việc )?vẽ|graph (bị )?tắt)'
  - 'regex:(?i)(bộ nhớ thứ cấp|secondary_memory)[^.]*(vẫn|không bị)'
rubric: "ĐẠT nếu tách được hai việc: graph tắt, bộ nhớ thứ cấp vẫn chạy nhờ stamp. KHÔNG đạt nếu nói cả hai cùng tắt hoặc cả hai cùng chạy."
---

# Golden: feature-switch-wikigraph-memory

Hỏi lại lỗi coupling đã sửa ở commit `86cdb6a8`. Hành vi khoá bằng `harness/tests/memory-map-user-reachability-test.sh` và `harness/tests/feature-switch-hooks-test.sh`.

## Origin
- Phiên coordinator 03/10/2026, branch `merge/setup-031026`. PLAN: `llmwiki/wiki/sources/draft/031026-harness-feature-switches-PLAN.md`.
