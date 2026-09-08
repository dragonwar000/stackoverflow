---
type: source
title: "R19 mở rộng code-line + cảnh báo SDK — port sang fork, giữ nguyên thiết kế opt-in của CHAT"
status: proposed
tags: [R19, evidence-terminal, code-line, sdk, port, graph-mode]
timestamp: 2026-09-08
---

# 080926-r19-code-line-port

## What

Đưa phần mở rộng R19 `evidence-terminal` (kind `code-line` + cảnh báo đỏ SDK) từ checkout
`~/Documents/Development/harness/setup` (nhánh fork `dragonwar000/setup`, phiên `57250149`) sang
repo này, và giải một xung đột **thiết kế** chứ không phải xung đột chữ.

## Luật mới nói gì

Kết luận về code phải neo vào **số dòng** (`path/file.ext:LINE`), và dòng neo **không được chỉ là
một lời gọi hàm** — `connect(url)` không chứng minh `connect` làm gì, nó chỉ chứng minh có ai đó
gọi nó. Dòng neo là lời gọi thì phải khai tiếp đúng một trong hai:

- `impl_ref` — dòng **định nghĩa** hàm đó trong source; validator mở đúng dòng ra kiểm nó thật sự
  khai báo hàm ấy.
- `sdk_doc` — hàm nằm trong SDK/thư viện: url tuyệt đối trỏ đúng mục + ngày tra + trích nguyên văn,
  **và** tài liệu phải mang một dòng chứa `🔴 CẢNH BÁO SDK`; thiếu dòng đó thì chuỗi bị chặn.

Khai cả hai là lỗi. Khai `sdk_doc` cho hàm mà `git grep` tìm thấy định nghĩa trong repo cũng là
lỗi — đang đọc mô tả thay vì đọc code đang chạy. Và `observed` trỏ vào file có đuôi mã nguồn bị từ
chối thẳng, vì nếu không thì đổi một chữ `kind` là né được toàn bộ luật trên.

## Xung đột thiết kế, và cách giải

Repo này đã **cố ý** chuyển luật chứng cứ tầng CHAT ra khỏi `CLAUDE.md`/`AGENT.md` vào skill
opt-in `/graph-mode` — vì nó nặng token và không phải phiên nào cũng cần (xem `ADR-004`: thứ gì
auto-bơm vào MỌI phiên chỉ được phục vụ dự án hiện tại). Patch mang sang lại đặt toàn bộ đoạn đó
trở lại `CLAUDE.md`, tức **revert quyết định kia** kèm theo nội dung mới.

Giải theo ranh giới *chi phí* chứ không theo bên nào:

| Phần | Về đâu | Vì sao |
|---|---|---|
| 7 loại điểm cuối, kỷ luật `code-line`, `impl_ref`/`sdk_doc` | `skills/graph-mode/SKILL.md` | Đây là kỷ luật **trích dẫn** — buộc mở file/trích dẫn nhiều hơn mỗi câu trả lời, đúng thứ đã bị đưa ra opt-in |
| Dòng `🔴 CẢNH BÁO SDK` (tầng CHAT) | `skills/graph-mode/SKILL.md` | Ban đầu tôi để nhãn này luôn-áp ở `CLAUDE.md` với lý do "giá một dòng chữ". User bác: mọi thứ khác đã ra opt-in thì nhãn cũng ra, `CLAUDE.md` chỉ giữ con trỏ. Đúng theo ADR-004 — ngoại lệ tự phong là cách một file auto-bơm phình lại |
| Dòng `🔴 CẢNH BÁO SDK` (tầng TÀI LIỆU) | validator, **luôn cắn** | Không đổi: tài liệu có khối ```evidence-chain mà lá tựa `sdk_doc` thì thiếu nhãn là R19 CHẶN, bất kể graph-mode. Chỗ ghi lại được có cổng cứng; chỗ không validator nào với tới (chat) là kỷ luật bật khi cần |
| Toàn bộ validator, fixture, policy, config, trang concept | Áp nguyên | Cổng máy chạy bất kể graph-mode bật hay tắt — không dính quyết định opt-in |

Cách kỹ thuật: `git apply --3way` trên diff working-tree của họ. 10/12 file sạch; hai file
`CLAUDE.md`/`AGENT.md` xung đột đúng ở đoạn nói trên và được giải tay theo bảng.

## Đo trên repo này, không tin số của họ

- **392 file `.md` trong `llmwiki/`, 0 file bị chặn.** (Bản của họ đo 339 file, 0 báo oan.)
- `evidence-terminal-test.sh` **21/21**, `evidence_terminal.py --self-test` PASS.
- `harness-doctor.py --ci` **19/19 rail cắn**.
- Bite-test trên **code thật của repo này** (`harness/scripts/token-budget.py`, `cost_usd` định
  nghĩa dòng 70, lời gọi dòng 117):

| Ca | Kỳ vọng | Kết quả |
|---|---|---|
| neo vào lời gọi trần | chặn | chặn |
| lời gọi + `impl_ref` đúng dòng định nghĩa | qua | qua |
| `impl_ref` trỏ sai dòng | chặn | chặn |
| `sdk_doc` cho hàm CÓ định nghĩa trong repo | chặn | chặn |
| neo thẳng dòng định nghĩa | qua | qua |
| `observed` trỏ file `.py` | chặn | chặn |

- Cảnh báo SDK (trên code root tạm có hàm ngoài source): thiếu dòng `🔴 CẢNH BÁO SDK` → **chặn**,
  kèm chỉ dẫn sửa · có dòng đó → **qua**, và cảnh báo đỏ **vẫn in ra terminal** (nó là cảnh báo,
  không phải lỗi) · bản không dấu `CANH BAO SDK` cũng tính.

Một lần đầu ca `observed` trỏ `.py` báo *không chặn* — hoá ra fixture của tôi hỏng (shell nuốt
backtick), không phải lỗ luật. Dựng lại bằng heredoc thì chặn đúng. Ghi lại vì đây là kiểu kết
luận sai dễ mắc nhất khi bite-test: fixture hỏng trông y hệt luật thủng.

## Lỗi phương ngữ regex — luật hụt trên Linux, local không thấy

CI đỏ đúng **một** ca mà local xanh 21/21: `code-line sdk cho ham noi bo — LOT`.

`_repo_defines` (nhánh đối chiếu "hàm này có định nghĩa trong repo không") shell ra
`grep -E` với một pattern viết bằng cú pháp **PCRE** — `(?:...)`. Nhưng `-E` ăn **ERE**, mà ERE
không có `(?:`. BSD grep trên macOS nuốt được nên local xanh; GNU grep trên Linux/CI trả
`rc=2 Invalid preceding regular expression`, mà hàm chỉ chấp `rc ∈ {0,1}` nên rơi xuống
`return None` — và `None` nghĩa là "bỏ qua đối chiếu".

Hệ quả lớn hơn một test đỏ: nhánh "khai `sdk_doc` cho hàm CÓ định nghĩa trong repo → lỗi"
**chết câm trên mọi máy Linux**, kể cả khi chạy trên repo thật. Không ai thấy, vì cổng câm
không đỏ.

Sửa: quét bằng `re` của **Python**, không shell ra `grep` nữa — pattern vốn được viết bằng cú
pháp Python (`re.escape`, `(?:`), nên chạy nó bằng chính engine đó là bỏ hẳn vấn đề phương ngữ.
Liệt kê file bằng `git ls-files` khi có, không phải repo thì đi bộ thư mục với danh sách bỏ qua
và trần 20 000 file / 2 MB mỗi file.

Neo lại bằng một assertion **liveness**, vì đây đúng là kiểu lỗi mà cổng câm không bắt được:
`_repo_defines` phải trả lời **dứt khoát** `True`/`False` cho hai ca đã biết, `None` là đỏ.
Negative control: ép `_candidate_files` trả `None` → test tụt 22/22 xuống 19/21, bắt đúng cả
assertion liveness lẫn ca `sdk_doc`-cho-hàm-nội-bộ.

Bài học lặp lại được: **local xanh trên macOS không chứng minh gì về Linux** khi cổng nào đó
shell ra công cụ hệ thống. Chỗ đáng nghi là mọi lần `subprocess` gọi `grep`/`sed`/`awk` với
regex.

## Trần đã biết (chép nguyên từ bản gốc, đã đọc code xác nhận)

Bộ dò lời gọi đọc **một dòng văn bản**, không dựng AST — bỏ chuỗi/comment trước khi đếm, nhận
dạng khai báo của ~8 ngôn ngữ, nhưng cú pháp lạ vẫn có thể đọc nhầm cả hai chiều. Việc "hàm này
có trong repo không" tra bằng `git grep`, chỉ để **đối chiếu** với khai báo của tác giả; tìm
không ra thì bỏ qua đối chiếu, cổng chính (phải khai `impl_ref` hoặc `sdk_doc`, cả hai đều có neo
kiểm được) vẫn cắn.

## Files

| File | Action |
|------|--------|
| `harness/validators/evidence_leaf.py` | modified — kind `code-line`, `call_targets`, `defines_symbol`, `_repo_defines`, `_read_anchor`, `sdk_backed_leaves`, `has_sdk_warning`, chặn `observed` trỏ mã nguồn |
| `harness/validators/evidence_terminal.py` | modified — cảnh báo đỏ + chặn tài liệu thiếu dấu `🔴 CẢNH BÁO SDK` |
| `llmwiki/.claude/hooks/validators/evidence_leaf.py` | modified — bản deploy tier-2 |
| `llmwiki/.claude/hooks/validators/evidence_terminal.py` | modified — bản deploy tier-2 |
| `harness/tests/evidence-terminal-test.sh` | modified — 10 fixture mới |
| `harness/scripts/harness-doctor.py` | modified — R19 thêm 2 rail `callsite:bat` / `impl:im` |
| `harness/policy.yaml` · `harness/poc-vendor-neutral/policy.yaml` | modified — statement R19 |
| `harness/evidence-terminal.config.yaml` | modified — ADAPT-CHECKLIST + trần đã biết |
| `llmwiki/wiki/concepts/evidence-terminal-chain.md` | modified — 6→7 loại, mục cảnh báo đỏ |
| `skills/graph-mode/SKILL.md` + mirror `llmwiki/skills/utils/graph-mode.md` | modified — **khác bản gốc**: kỷ luật trích dẫn về đây thay vì về CLAUDE.md |
| `llmwiki/CLAUDE.md` · `llmwiki/AGENT.md` | modified — chỉ đổi "6 loại"→"7 loại"; khung opt-in giữ nguyên, KHÔNG chép luật ra ngoài |
| `fdk/skills.provenance.json` | modified — ghi lại checksum `graph-mode` |

## Notes

- Nguồn: `~/Documents/Development/harness/setup/llmwiki/wiki/draft/cave/080926-r19-code-line-sdk-warning.md` (phiên `57250149`, chưa commit ở checkout đó)
- Bản này **không** chép nguyên tầng CHAT — xem bảng "Xung đột thiết kế" ở trên.
- Vòng sửa sau phản hồi user: nhãn `🔴 CẢNH BÁO SDK` ở tầng CHAT chuyển nốt vào `/graph-mode`.
  `CLAUDE.md`/`AGENT.md` trở lại đúng trạng thái trước đợt này, khác mỗi con số 6→7 loại.

## Origin

- **Draft:** `wiki/sources/draft/080926-r19-code-line-port.md`
- **Commit:** _(filled by verify-before-commit)_
- **Date promoted:** _(filled by verify-before-commit)_
