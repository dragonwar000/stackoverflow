---
type: source
title: "Vòng merge 2 — ba giả thuyết sai trước khi tìm ra chỗ lệch thật"
status: proposed
tags: [merge, upstream, ci-local, provenance, diagnosis]
timestamp: 2026-09-08
---

# 080926-merge-round2-upstream

## What

Kéo tiếp 14 commit upstream (`ed4ba62` → `ddd366dc`) vào fork trong cùng ngày, và ba lần
chẩn đoán sai trước khi tìm ra nguyên nhân thật của một cổng CI đỏ.

## Merge

Một xung đột duy nhất: `fdk/skills.search.json` — chỉ mục BM25 **sinh ra**. Không hoà giải
tay file sinh; chạy lại `build-skill-search.py`. Cùng nguyên tắc đã dùng cho
`eval-baseline.json`: artifact sinh thì regen, không merge.

Phần mới đáng chú ý từ upstream: gom mọi artifact sinh/kéo về một gốc `.overstack/`;
`fdk/tools/ci-local.py` chạy **trọn** mọi step CI GitHub tại local (thay đúng cái script
ad-hoc tôi tự dựng vòng trước); `/prd-grade-fe`; bỏ mirror thứ ba `llmwiki/wiki/skills`
(68 file, nên số `.md` trong `llmwiki/` tụt 393 → 332).

Kiểm phần riêng của fork sau merge: 0 conflict marker · 0 `.pyc` được track · 5 file đường
cài vẫn trỏ `dragonwar000/stackoverflow` và 0 chỗ trỏ `Rheinmir` · R19 `code-line` + bản vá
phương ngữ regex còn đủ · `CLAUDE.md` giữ khung opt-in · plugin status bar còn nguyên.

## Ba giả thuyết sai — và cái đo được đã bác chúng

`ci-local.py` cho 59/62. Ba đỏ, và tôi đoán sai cả ba lần đầu.

**1 · `wiki-graph user-reachability` tụt 18/18 → 15/1.** Đoán: merge làm hỏng đường resolve.
Đo: tái hiện trên worktree upstream **nguyên** — cũng đỏ y hệt, mà GitHub Actions của upstream
báo `harness` **SUCCESS** trên đúng commit đó. Nên không phải repo. Nguyên nhân thật: bản
global tôi cài trước đó đã **cũ so với cây sau merge**. Cài lại `install-harness.sh --global`
→ 18/18. Bài học: cài global từ working-tree thì **mỗi vòng merge phải cài lại**.

**2 · `harness-update — idempotent tốc độ 12-20s >= 5s`.** Đoán: bản vá `_repo_defines` của
tôi (đổi `grep` thành vòng Python) làm chậm. Đo A/B: tắt **hẳn** scanner (`return None` ngay)
thì cổng vẫn 14.5s; worktree upstream nguyên cũng 12.5s trên máy này. Máy chậm hơn runner ở
phép đo đó, không phải hồi quy. Giữ lại phần tối ưu (cache + tiền-lọc bytes: hit 1071 ms →
63 ms, gọi lại cùng tên 0 ms) **vì nó thật, không vì nó chữa cổng** — và ghi rõ thế trong
commit để không ai đọc nhầm.

**3 · `skill-provenance` đỏ 3 skill trên CI, local xanh 89/89.** Đoán lần lượt: (a) sổ ghi
file untracked — sai, file set khớp `git ls-files` 11/11, 9/9, 2/2; (b) commit `eefc15cb` đổi
cổng sang **đọc git thay vì đọc đĩa** nên bản ghi lúc merge chưa commit bị lệch — sai, đọc
code thì `skill-provenance` dùng `rglob` + `read_bytes`, tức đọc đĩa; (c) CI chạy sha khác —
sai, đúng head, và merge-ref có `main` là tổ tiên nên tree bằng nhau.

Chỉ khi so **ba chiều remote/đĩa/sổ** mới thấy: hash file khớp ở cả ba nơi, còn **SỔ** trên
remote vẫn là bản upstream cũ. Nguyên nhân: `git commit` trên một **merge commit** ghi theo
**INDEX**. Tôi chạy `record` sau khi giải xung đột nhưng trước khi commit và **không
`git add` lại** — index giữ bản của merge, worktree giữ bản đúng, nên `check --ci` (đọc đĩa)
báo xanh trong khi commit thì sai.

**Dấu hiệu nhận biết đáng ghi:** *local xanh + CI đỏ trên cùng một sha* gần như luôn nghĩa là
**thứ được commit khác thứ trên đĩa** — hãy so cái đã commit, đừng so cái đang mở.

## Nợ môi trường còn lại (CI không chạm tới)

`ge-travel` bước (e): `fresh-install-smoke` so skill trên đĩa với `~/.agents/skills` của MÁY;
thiếu 5 skill mới (`diagram`, `doyourmagic`, `graph-mode`, `playwright-verify`,
`prd-grade-fe`). Khối đó có guard `[ -d "$SK_DIR" ]` nên CI bỏ qua. Sửa bằng
`npx skills add . --global --all`, không phải sửa repo.

## Files

| File | Action |
|------|--------|
| 400+ file từ 14 commit upstream (gồm rename sang `.overstack/`) | merged |
| `fdk/skills.search.json` | regenerated (xung đột duy nhất) |
| `fdk/skills.provenance.json` | modified — ghi lại 3 skill |
| `harness/validators/evidence_leaf.py` + bản deploy tier-2 | modified — cache + tiền-lọc bytes |
| `llmwiki/wiki/sources/draft/080926-merge-round2-upstream.md` | created |

## Notes

- Đối chiếu CI tại local bằng `ci-local.py` của upstream, không còn script ad-hoc.
- CI trên PR #1: 5/5 xanh sau khi commit sổ.

## Origin

- **Draft:** `wiki/sources/draft/080926-merge-round2-upstream.md`
- **Commit:** _(filled by verify-before-commit)_
- **Date promoted:** _(filled by verify-before-commit)_
