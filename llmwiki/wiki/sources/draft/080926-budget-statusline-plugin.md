---
type: source
title: "Plugin status bar % trần chi tiêu — và chỗ Claude Code không cho plugin tự cắm"
status: proposed
tags: [plugin, statusline, token-budget, finops, orca]
timestamp: 2026-09-08
---

# 080926-budget-statusline-plugin

## What

Plugin `overstack-budget-statusline`: thanh trạng thái hiển thị % bốn trần chi tiêu overstack
(token · $ · model-call · tool-call) cộng cửa sổ ngữ cảnh sống, kèm dấu cho trần **thực sự
chặn được phiên**.

## Hai giới hạn đo được TRƯỚC khi viết

**Orca không có chỗ để cắm.** `orca agent-context` khai 234 lệnh; lọc theo
`status|plugin|badge|title` ra **rỗng**. Bề mặt UI ghi được chỉ là `worktree set
--display-name`, `terminal rename`, `worktree set --comment` — đều phải poll, không phải status
bar. Thanh mà người dùng nhìn thấy trong một phiên Orca **là** statusLine của Claude Code chạy
trong terminal Orca nhúng.

**Plugin Claude Code không khai được `statusLine`.** `plugin.json` không có field đó; plugin chỉ
ship được `subagentStatusLine` qua `settings.json` của plugin, mà cái đó là hàng phụ dưới prompt
chứ không phải thanh chính. Nên hình dạng đúng là: plugin mang script + một lệnh slash, còn
`/budget-statusline install` ghi khoá `statusLine` vào `~/.claude/settings.json`. Một bước bật
tay, có chủ ý — không phải hạn chế lách được.

## Output

`plugins/overstack-budget-statusline/` — `plugin.json` · `statusline.py` (engine + install/
uninstall/status/self-test) · `commands/budget-statusline.md` · `README.md`. Publish qua entry
thứ tư trong `.claude-plugin/marketplace.json`.

```
[CAVEMAN] Opus ctx ▓░░░░░░░░░ 14%/1M
budget tok 7%▲(139.8k) · $ 42%($2.09) · calls 33%▲(163) · tools 8%(159)  ▲=chặn@85% mode:warn
```

Ba quyết định đáng ghi:

- **Không nuốt statusLine đang có.** Bản cũ cất ở `_overstackBudgetStatuslinePrev`, badge của nó
  vẫn được gọi rồi ghép vào đầu dòng 1 (đo thật: `[CAVEMAN]` còn nguyên). `--uninstall` trả lại
  đúng nguyên trạng.
- **`▲` chỉ đánh cho trần nằm trong `auto_handover.triggers`.** Đây là trần DUY NHẤT thi hành
  thật; `mode: warn` khiến `check` chỉ cảnh báo. Vẽ cả bốn trần như nhau là nói dối về mức độ
  ràng buộc.
- **Phiên chưa có row trong ledger → nói thẳng "chưa có số", không vẽ `0%`.** Một số 0 bịa ra
  còn tệ hơn một ô trống.

## Hai lỗi chỉ lộ ra khi CHẠY THẬT

**1 · Đường dẫn có dấu bị escape.** `--install` dựng chuỗi lệnh bằng `json.dumps(path)`; mặc
định `ensure_ascii=True` nên `pull-code-mới-từ-setup` thành `pull-code-m\u1edbi-t\u1eeb-setup`.
Hệ quả kép: lệnh trỏ vào đường dẫn KHÔNG TỒN TẠI (thanh câm, fail-open nên không báo gì), và
`--status`/`--uninstall` so chuỗi thô với bản đã escape nên không nhận ra chính nó — báo "lệch
đường dẫn" giả rồi từ chối gỡ. Sửa: `shlex.quote` (công cụ đúng cho trích dẫn shell) và so
sánh trên chuỗi lệnh sống thay vì trên `json.dumps` của nó.

Chỉ lộ vì worktree này có tên tiếng Việt. Trên một đường dẫn ASCII, self-test vẫn xanh và bug
đi thẳng ra người dùng.

**2 · So sánh đường dẫn khi có symlink.** `tempfile` trên macOS trả `/var/...` còn `resolve()`
ra `/private/var/...`; assertion so hai thứ đó đỏ dù code đúng. Sửa ở test, không ở code.

## Neo lại bằng cổng

`harness/tests/budget-statusline-test.sh`, wire vào `harness.yml`. Sáu assertion, trong đó hai
cái self-test của plugin **không** tự kiểm được: plugin có mặt trong marketplace (thiếu thì
`/plugin install` không thấy), và công thức `$` khớp `token-budget.py:cost_usd` trên 3 ca (lệch
thì thanh và `--report` nói khác nhau, không ai tin cái nào).

Negative control: gỡ entry marketplace → 1 vi phạm; bẻ công thức `$` → bắt đúng chỗ.

## Nợ mở đã khai, không tự vá

`rates` trong `token-budget.config.yaml` không có khoá `claude-opus-5`, nên model id thật rơi về
`default` (0.003/0.015) và `$` **thấp hơn giá Opus thật**. Plugin cố ý không tự thêm khoá — calib
giá là quyết định của người dùng (`verified: false`), không phải của status bar. README nói rõ.

## Files

| File | Action |
|------|--------|
| `plugins/overstack-budget-statusline/.claude-plugin/plugin.json` | created |
| `plugins/overstack-budget-statusline/statusline.py` | created |
| `plugins/overstack-budget-statusline/commands/budget-statusline.md` | created |
| `plugins/overstack-budget-statusline/README.md` | created |
| `harness/tests/budget-statusline-test.sh` | created |
| `.claude-plugin/marketplace.json` | modified (entry thứ tư) |
| `.github/workflows/harness.yml` | modified (wire cổng mới) |
| `llmwiki/wiki/index.md` | modified |

## Notes

- Cài: `/plugin marketplace add <repo>` → `/plugin install overstack-budget-statusline@rheinmir-setup-skills` → `/budget-statusline install`
- `${CLAUDE_PLUGIN_ROOT}` đổi sau mỗi lần cập nhật plugin → phải chạy lại `install`; `--status` phát hiện ca này.

## Origin

- **Draft:** `wiki/sources/draft/080926-budget-statusline-plugin.md`
- **Commit:** _(filled by verify-before-commit)_
- **Date promoted:** _(filled by verify-before-commit)_
