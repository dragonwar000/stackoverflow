---
type: draft
title: "Merge upstream Rheinmir/setup@orca (106 commit) vào dragonwar000/stackoverflow"
status: proposed
tags: [merge, upstream, fork-identity, egress-guard, ci-parity, output-report]
timestamp: 2026-09-08
---

# 080926-merge-upstream-setup

## What

Kéo toàn bộ phần mới của repo gốc `Rheinmir/setup@orca` từ điểm rẽ nhánh `14ffaec`
(30/07) tới `ed4ba62` (08/09) vào `dragonwar000/stackoverflow@main`, giữ nguyên phần
định danh riêng của fork, và đối chiếu luồng CI tại local trước khi push.

## Output

**Đo trước khi làm.** `merge-base` = `14ffaec`. Upstream đi tiếp **106 commit**, fork đi
**13 commit** — hai bên đã thật sự rẽ, không phải một bên chứa bên kia. Mười ba commit
riêng của fork chạm đúng 10 file, trong đó bốn file là *định danh repo*
(`README.md`, `bootstrap.sh`, `bootstrap-fork.sh`, `install-harness.sh`) — chỗ merge dễ
âm thầm kéo ngược về `Rheinmir/setup` nhất.

**Ba xung đột, mỗi cái giải theo bằng chứng chứ không theo "ours/theirs" mặc định:**

| File | Giải | Bằng chứng |
|------|------|-----------|
| `harness/poc-vendor-neutral/install.sh` | Lấy `$OVERSTACK_DIR` của upstream, giữ `REPO_RAW` + `SKILLS_REF` trỏ `dragonwar000/stackoverflow` | Hai thay đổi độc lập nhau — cải tiến biến đường dẫn không đụng gì tới nguồn tải |
| `harness/scripts/egress-guard.py` | Lấy trọn bản upstream | `diff` bản fork ↔ bản upstream: upstream là **superset** — có cả fix "gắn domain với lệnh net thật" của fork (`be3d679`), cộng lớp `_NOT_A_TLD` + `bare_ok` chống báo oan `bootstrap.sh`/`spec.loader` |
| `llmwiki/wiki/index.md` | Lấy khối upstream | Hai dòng của fork mô tả cùng nội dung với hai dòng `-1319b8e1` của upstream; file trên đĩa sau merge đúng là bản upstream (`300726-session-provenance.md` = phiên `0121bc61`), nên giữ dòng fork sẽ thành index trỏ sai |

**Hai việc dọn ngoài xung đột.** Upstream còn track 54 file `.pyc` (mới, dưới
`skills/last30days/`); fork đã gỡ `.pyc` khỏi git và chặn `__pycache__/` trong
`.gitignore` từ `aebb940`. Merge kéo chúng vào lại → `git rm --cached` cả 54 file cho
khớp chính sách fork. Và đã soi lại toàn cây: mọi chỗ còn hardcode `Rheinmir/setup`
(`version.json`, `.template-manifest.json`, `fdk-kit.sh`, `harness-events.py`…) đều
**đã có sẵn y hệt** trong `stackoverflow/main` từ trước — đó là con trỏ upstream có chủ
ý của template-sync, không phải drift do merge sinh ra.

**Đối chiếu CI tại local trước push** (rule FDK: ship push luôn đối chiếu luồng CI
GitHub tại local). Tất cả xanh:

- `demo.sh` 13/13 · `test-broad.sh` 80/80
- `wiki-graph-user-reachability` 18/18 · `memory-map-user-reachability` 13/13
- `index_sync` (fdk/wiki + llmwiki/wiki) · `wiki-health --fail-on broken`
- `arch-scan` 90 file sạch · `code_health` 142 file compile sạch
- `harness-lint --check` 0 drift · `agent_claude_parity` 88 skill khớp
- `duplicate_basename` · `build-capabilities.py --check` · `adapt-registry --check` (89 hằng số quarantine, 0 rò) · `tests-wired`

**Nghiệm thu cuối.** `git diff HEAD origin/orca` sau merge chỉ còn đúng 7 file — 5 file
định danh fork + 2 bản `orca-onboard` — cộng 54 `.pyc`. Không sót phần upstream nào,
không mất phần fork nào.

## Files

| File | Action |
|------|--------|
| `harness/poc-vendor-neutral/install.sh` | modified (giải xung đột) |
| `harness/scripts/egress-guard.py` | modified (giải xung đột) |
| `llmwiki/wiki/index.md` | modified (giải xung đột) |
| 410 file khác từ 106 commit upstream | merged |
| 54 file `.pyc` dưới `skills/last30days/scripts/lib/__pycache__/` | untracked (`git rm --cached`) |
| `llmwiki/wiki/draft/cave/080926-merge-upstream-setup.md` | created |

## Notes

- Invoked via: `/caveman` skill (output report)
- Commit merge: `e493ac29`, push thẳng vào `main` theo lựa chọn của user
- Lưu ý còn treo: workflow `harness.yml` chỉ trigger `push` trên nhánh `orca`, nên push
  vào `main` của fork **không** chạy CI trên GitHub — đó là lý do phải đối chiếu tại
  local. Muốn CI tự gác fork thì thêm `main` vào `on.push.branches`.

## Origin

- **Draft:** `wiki/draft/cave/080926-merge-upstream-setup.md`
- **Commit:** _(filled by verify-before-commit)_
- **Date promoted:** _(filled by verify-before-commit)_
