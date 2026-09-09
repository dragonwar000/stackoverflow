# overstack-budget-statusline

Status bar cho một phiên làm việc: % bốn trần chi tiêu của overstack, cộng cửa sổ ngữ cảnh
sống, cộng dấu cho trần **thực sự chặn được phiên**.

```
[CAVEMAN] Opus ctx ▓░░░░░░░░░ 14%/1M
budget tok 7%▲(139.8k) · $ 42%($2.09) · calls 33%▲(163) · tools 8%(159)  ▲=chặn@85% mode:warn
```

## Vì sao là plugin + một lệnh, chứ không phải một field trong `plugin.json`

Claude Code **không** cho plugin khai `statusLine` — `plugin.json` không có field đó, và
`settings.json` của plugin chỉ nhận `agent` với `subagentStatusLine` (hàng phụ dưới prompt,
không phải thanh chính). Nên plugin mang script, còn `/budget-statusline install` ghi khoá
`statusLine` vào `~/.claude/settings.json` trỏ về script đó. Một bước bật tay, có chủ ý.

Orca cũng không có chỗ nào khác để cắm: `orca agent-context` khai 234 lệnh, không lệnh nào
chạm status bar hay plugin. Thanh mà bạn nhìn thấy trong một phiên Orca **là** statusLine của
Claude Code chạy trong terminal Orca nhúng.

## Cài

```
/plugin marketplace add /đường/dẫn/tới/repo     # repo này đã là marketplace sẵn
/plugin install overstack-budget-statusline@rheinmir-setup-skills
/budget-statusline install
```

`install` **không nuốt** statusLine đang có: bản cũ được cất ở khoá
`_overstackBudgetStatuslinePrev`, và badge của nó vẫn được gọi rồi ghép vào đầu dòng 1 (ví dụ
`[CAVEMAN]`). `/budget-statusline uninstall` trả lại nguyên trạng.

⚠️ `${CLAUDE_PLUGIN_ROOT}` đổi sau mỗi lần cập nhật plugin, nên cập nhật xong hãy chạy lại
`/budget-statusline install`. `/budget-statusline status` phát hiện được ca lệch đường dẫn.

## Nó đọc gì

| Phần | Nguồn | Nhịp cập nhật |
|---|---|---|
| Cửa sổ ngữ cảnh, model | JSON stdin Claude Code đưa vào | mọi lượt (debounce 300ms) |
| tok · $ · calls · tools | `harness/metrics/tokens.jsonl` | hook `Stop`, tức mỗi lượt trả lời |
| Trần, ngưỡng, mode | `harness/token-budget.config.yaml` | khi bạn sửa file |

Nhận cả layout `harness/` (repo framework) lẫn `.harness/` (dự án đích sau bản dot-layout),
và leo ngược thư mục cha để tìm gốc.

Cách cộng dồn **giống hệt** `harness/scripts/token-budget.py:totals()` — mọi row cộng dồn, và
`$` luôn **tính lại** từ `(in, out, model, rates)` chứ không đọc field `usd` của row. Lệch cách
cộng thì thanh nói một đằng, `token-budget.py --report` nói một nẻo, và không ai tin cái nào nữa.

## Đọc thanh thế nào

- Màu: xanh <60% · vàng 60–85% · đỏ ≥85%.
- `▲` = trần này nằm trong `auto_handover.triggers`, tức **chạm ngưỡng là bàn giao + mở phiên
  mới thật**. Trần không có `▲` chỉ là con số để nhìn.
- `mode:warn` = `token-budget.py check` chỉ cảnh báo, không chặn. Cổng duy nhất còn cắn là
  auto-handover.
- Phiên chưa có row nào trong ledger → thanh nói thẳng *"chưa có số cho phiên này"* thay vì vẽ
  `0%`. Một số 0 bịa ra còn tệ hơn một ô trống.

## Hai điều thanh này KHÔNG nói dối về

1. **`$` là số quy đổi, không phải hoá đơn.** `token-budget.config.yaml` đang `verified: false`
   — rates là số minh hoạ chưa đối chiếu bảng giá. Tệ hơn: model id thật (`claude-opus-5`)
   không khớp khoá `opus` trong `rates`, nên rơi về `default` (0.003/0.015) và **thấp hơn giá
   Opus thật**. Muốn đúng thì thêm khoá `claude-opus-5` vào `rates`. Plugin cố ý không tự sửa —
   calib giá là quyết định của người dùng, không phải của status bar.
2. **Cửa sổ ngữ cảnh khác trần harness.** `ctx` là cửa sổ của model (từ Claude Code), còn
   `tok` là trần chi tiêu của overstack. Hai trục độc lập; thanh để cạnh nhau nhưng không cộng.

## Kiểm

```
python3 statusline.py --self-test     # 18 assertion, tất định, không cần Claude Code
```

Phủ: bộ đọc config (cắt chú thích, list, flow-mapping lồng) · công thức `$` khớp
`token-budget.py` · cộng dồn ledger nhiều row và loại phiên khác · tìm gốc cả hai layout và leo
ngược · render hai dòng · phiên rỗng nói thẳng thay vì vẽ 0% · ngoài overstack không nổ ·
trường context `null` không nổ · ngưỡng màu · làm tròn thanh.

Fail-open tuyệt đối: mọi lỗi đều nuốt và exit 0. Status bar không bao giờ được làm hỏng phiên.
