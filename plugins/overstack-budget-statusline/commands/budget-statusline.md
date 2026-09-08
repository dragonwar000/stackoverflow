---
description: Bật/tắt/kiểm status bar hiển thị % trần token·$·calls·tools của overstack
argument-hint: install | uninstall | status | preview | self-test
allowed-tools: Bash(python3:*), Bash(echo:*), Read, Edit
---

Người dùng gõ `/budget-statusline $ARGUMENTS`.

Script nằm ở `${CLAUDE_PLUGIN_ROOT}/statusline.py`. Chạy đúng một lệnh dưới đây theo
`$ARGUMENTS` (rỗng thì coi như `status`), rồi thuật lại kết quả gọn — đừng thêm bước nào
người dùng không xin.

| `$ARGUMENTS` | Chạy |
|---|---|
| `install` | `python3 "${CLAUDE_PLUGIN_ROOT}/statusline.py" --install` |
| `uninstall` | `python3 "${CLAUDE_PLUGIN_ROOT}/statusline.py" --uninstall` |
| `status` hoặc rỗng | `python3 "${CLAUDE_PLUGIN_ROOT}/statusline.py" --status` |
| `self-test` | `python3 "${CLAUDE_PLUGIN_ROOT}/statusline.py" --self-test` |
| `preview` | dựng payload giả rồi đẩy vào script — xem mẫu bên dưới |

Mẫu `preview` (không đụng settings, chỉ để xem thanh trông thế nào):

```bash
echo '{"session_id":"'"$(python3 -c 'import os;print(os.environ.get("CLAUDE_SESSION_ID",""))')"'","cwd":"'"$PWD"'","model":{"display_name":"Opus"},"context_window":{"used_percentage":14,"context_window_size":1000000}}' \
  | python3 "${CLAUDE_PLUGIN_ROOT}/statusline.py"
```

Sau `install`, nói cho người dùng ba điều — không bịa thêm:

1. Thanh mới hiện ở lượt kế tiếp (Claude Code chạy lại statusLine theo sự kiện).
2. Nếu trước đó họ đã có statusLine khác, nó được cất ở khoá `_overstackBudgetStatuslinePrev`
   và badge cũ vẫn hiện ở đầu dòng 1 — `uninstall` trả lại nguyên trạng.
3. Đường dẫn plugin đổi sau mỗi lần cập nhật plugin, nên cập nhật xong phải chạy lại
   `/budget-statusline install`. Lệnh `status` phát hiện được ca lệch đường dẫn này.

Nếu `install` báo không tìm thấy overstack từ thư mục hiện tại: thanh vẫn cài được và vẫn
hiện cửa sổ ngữ cảnh, chỉ là dòng trần sẽ trống cho tới khi chạy trong một dự án có
`harness/token-budget.config.yaml` (hoặc `.harness/`). Nói đúng như vậy, đừng hứa hơn.
