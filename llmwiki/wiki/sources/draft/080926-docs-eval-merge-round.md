---
type: source
title: "Trang tài liệu + hai golden eval cho đợt merge upstream 08/09"
status: proposed
tags: [docs-site-macos, wikieval, merge, output-report]
timestamp: 2026-09-08
---

# 080926-docs-eval-merge-round

## What

Dựng trang tài liệu single-file cho đợt merge `Rheinmir/setup@orca` → `dragonwar000/stackoverflow@main`
ngày 08/09, và neo hai bài học của đợt merge đó thành golden eval hồi quy.

## Output

**Trang tài liệu** — `llmwiki/html/080926-merge-upstream-setup.html`, 6 mục theo hệ macOS
liquid-glass: bối cảnh rẽ nhánh · ba xung đột · dọn ngoài xung đột · CI tại local · nghiệm
thu + eval · nợ mở. Sáu sơ đồ SVG kéo-thả được (36 node), mind map bezier, theme sáng/tối,
copy-button cho 7 khối code, sidebar collapse. Tự chứa hoàn toàn — 0 request ra ngoài.

Đã kiểm bằng trình duyệt thật, không đọc-rồi-đoán:

| Kiểm | Kết quả |
|------|---------|
| console error | 0 |
| tag balance · id trùng · nav anchor | sạch |
| `node --check` toàn bộ JS inline | OK |
| tràn ngang | phát hiện `scrollWidth 1606 > 1512` → vá `main{overflow-x:clip}` → hết |
| dark theme | token đổi đúng; phát hiện chữ SVG `#4a4a55` chìm trên nền tối → thêm 3 rule override |
| collapse | `max-height` đo bằng `scrollHeight` (582px), không cap cứng |

Hai lỗi trên đều **chỉ lộ ra khi chạy**: dải tint `100vw` tràn vì `body` có `padding-left`
cho sidebar, và SVG dùng presentation attribute nên không ăn token màu của theme.

**Hai golden eval** trong `fdk/wiki/sources/evals/`:

- `merge-fork-identity` — trong một hunk có thể trộn cải tiến CẤU TRÚC (lấy) với dòng ĐỊNH
  DANH (giữ), nên `ours/theirs` cả file là sai; nghiệm thu bằng grep đường cài **cộng** diff
  cây merge với upstream, đọc kết quả theo cả hai chiều dư/thiếu.
- `merge-superset-conflict` — đo quan hệ hai bản bằng `diff` TRƯỚC khi chọn; superset thì lấy
  trọn một bên và nói ra được vì sao không mất gì; không bao nhau thì hợp nhất tay.

**Baseline eval dựng lại.** Baseline commit từ 18/07 ghi 4 golden pass nhưng bộ candidate
output đi kèm chỉ có 2 mục, nên `--check` báo hồi quy giả cho `adapt-modes-pick` và
`capproof-liveness` — nợ có sẵn, chưa ai chạm vì `--check` không được wire vào CI (chỉ
`--self-test` nằm trong `fdk-gate.py`). Bù output cho 3 golden còn thiếu → 7/7 decided, ghi
lại baseline. Chứng minh gate còn cắn: bẻ một output → `--check` exit 2 đúng golden đó.

## Files

| File | Action |
|------|--------|
| `llmwiki/html/080926-merge-upstream-setup.html` | created |
| `fdk/wiki/sources/evals/merge-fork-identity.md` | created |
| `fdk/wiki/sources/evals/merge-superset-conflict.md` | created |
| `fdk/wiki/index.md` | modified (2 dòng eval) |
| `harness/evals/wikieval-outputs.example.json` | modified (2 → 7 candidate output) |
| `harness/metrics/eval-baseline.json` | modified (4 → 7 golden, 2026-09-08) |
| `llmwiki/wiki/index.md` | modified (dòng index cho draft này) |

## Notes

- Invoked via: `/docs-site-macos` + `wikieval` skill
- Xem trang: `llmwiki/html/080926-merge-upstream-setup.html`
- Bản ghi đợt merge: [[080926-merge-upstream-setup]]

## Origin

- **Draft:** `wiki/sources/draft/080926-docs-eval-merge-round.md`
- **Commit:** _(filled by verify-before-commit)_
- **Date promoted:** _(filled by verify-before-commit)_
