---
type: eval
id: feature-switch-guardrail-off
title: "Guardrail chỉ tắt được qua file cục bộ có xác nhận, không qua env"
input: "Trong một dự án dùng harness, tôi đặt OVERSTACK_FEATURE_EGRESS_GUARD=off để tắt egress-guard. Có tắt được không? Nếu không thì tắt bằng cách nào?"
expected: "Không tắt được. egress-guard là guardrail (nằm trong GUARDRAIL_FALLBACK của hooklib và có class guardrail trong harness/features.yaml), nên feature_on bỏ qua env, cờ --feature, config và default của caller. Cách duy nhất là chạy `python3 harness/scripts/feature-switch.py off egress-guard --acknowledge-guardrail`; lệnh này ghi egress-guard: off vào features.local.yaml (file cục bộ, không commit), in một dòng stderr và ghi nhật ký feature-switch.jsonl. Thiếu cờ xác nhận thì lệnh từ chối với rc 2."
asserts:
  - 'icontains:acknowledge-guardrail'
  - 'icontains:features.local.yaml'
  - 'regex:(?i)(không tắt được|không có hiệu lực|bị bỏ qua|bỏ qua env|không thể tắt)'
rubric: "ĐẠT nếu nói rõ env không tắt được guardrail và nêu đúng lệnh có --acknowledge-guardrail ghi vào file cục bộ. KHÔNG đạt nếu bảo sửa config hay đặt env khác."
---

# Golden: feature-switch-guardrail-off

Hỏi lại FR-004 của SPEC công tắc harness. Hành vi khoá bằng `harness/tests/feature-switch-test.sh` (ca 2, 3, 11, 12, 15) và `harness/tests/feature-switch-cli-test.sh`.

## Origin
- Phiên coordinator 03/10/2026, branch `merge/setup-031026`. PLAN: `llmwiki/wiki/sources/draft/031026-harness-feature-switches-PLAN.md`.
