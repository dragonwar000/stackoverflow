---
type: draft
title: "031026-recent-work-report"
status: proposed
tags: [docs-site-macos, output-report, zeromem, feature-switch, merge]
timestamp: 2026-10-03
---

# 031026-recent-work-report
**Type:** draft
**Status:** proposed
**Tags:** docs-site-macos, output-report
**Proposed:** 2026-10-03

## What
Trang tài liệu tổng kết năm việc gần đây trên branch `merge/setup-031026`: hợp nhất upstream, zeromem, công tắc harness, sự cố orchestration, và các phát hiện khi kiểm code.

## Output
- Trang `llmwiki/html/031026-recent-work-report.html`. Cổng tĩnh `frontend-antipattern.py` rc 0. Cổng chạy thật `html-visual-gate.mjs` 1/1 đạt, không còn cảnh báo.
- Trang khai `overstack-shell: none`: dùng khung của trang companion đã qua cổng, không có mind map và icon tile của `docs-site-macos`.
- Chưa chạy Playwright audit riêng của skill `docs-site-macos` và chưa bật Auto-Host. Cổng chạy thật đã kiểm nút đổi giao diện và tương phản.
- Eval chưa làm: skill `wikieval` chặn agent gọi, người dùng tự chạy `/wikieval`.

## Trạng thái các việc được ghi trong trang
| Việc | Commit | Kiểm chứng |
|---|---|---|
| Hợp nhất 167 commit upstream | `c4a8e318` | swh-lint 83/83, skill-provenance 106/106; chưa chạy `ci-local.py` |
| zeromem T1 cài và ghim | `06d52149` | `zeromem-install-test.sh` 3/3 |
| zeromem T2 bridge | `7f19b1a9` | `zeromem-bridge-test.sh` 5/5 |
| zeromem T3 khoá backend | `a22ac262` | `zeromem-bridge-test.sh` 10/10 |
| zeromem T4 nối hook | đang chạy (`ctx_c7aecc9ce8b5`) | chưa có |
| Công tắc harness SPEC và PLAN | `5071bb3e`, `f08c2b41` | R7 đạt; chưa dispatch |

## Files
| File | Action |
|------|--------|
| `llmwiki/html/031026-recent-work-report.html` | created |
| `llmwiki/wiki/sources/draft/031026-recent-work-report.md` | created |
| `llmwiki/wiki/index.md` | modified |
| `llmwiki/wiki/log.md` | modified |

## Notes
- Invoked via: yêu cầu bổ sung tài liệu của hook R10.
- Việc còn mở: lệch `statement` ở 20 rule giữa hai file policy; ba FAIL của preset archify trên các sơ đồ `-tN.html`; bản fork archify `macos` chưa cài.

## Origin
- **Draft:** `wiki/sources/draft/031026-recent-work-report.md`
- **Commit:** _(filled by verify-before-commit)_
- **Date promoted:** _(filled by verify-before-commit)_
