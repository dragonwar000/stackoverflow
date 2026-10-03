---
type: draft
title: "zeromem chạy song song với mem-rank và memory-map"
status: proposed
tags: [memory, zeromem, mem-rank, memory-map, propose]
timestamp: 2026-10-03
---

# 031026-zeromem-parallel-backend

**Status:** proposed

**Sequence diagram:** [trang companion theo task](../../../html/031026-zeromem-parallel-backend-seq.html)

## What

Thêm zeromem làm backend memory chính, chạy song song với mem-rank và memory-map. Backend mặc định là zeromem. mem-rank vẫn giữ nguyên hành vi và có thể chọn bằng khoá config, hoặc chạy cả hai.

## Context

Hệ memory hiện tại có hai phần đã chạy được. Phần ghi là `secondary_memory` trong `llmwiki/.claude/hooks/stop.py`, gọi `mem-rank episode` với `did` là subject commit gần nhất và danh sách file đã đổi, không chứa nội dung hội thoại. Phần đọc là `recall` trong `llmwiki/.claude/hooks/session_start.py`, in chuỗi phiên gần nhất. Theo [[log-model]] (`llmwiki/wiki/concepts/log-model.md`), `memory.jsonl` là sổ local, gitignored, trả lời câu hỏi "phiên trước đã làm gì", và không được ép phối hợp chặt với các sổ khác. Đề xuất này giữ nguyên nguyên tắc đó: zeromem là một sổ mới, không đổi `events.jsonl`, `scratch-log`, `provenance-log` hay `ledger.jsonl`.

Theo ADR-009 (`llmwiki/wiki/sources/adr/ADR-009-session-orientation-autoindex-forcequery.md`), mọi draft phải force-query wiki trước khi viết. Các mục dưới đây đã được đối chiếu với wiki và code.

Về zeromem, đã kiểm chứng trên máy này. Binary `zm` được cài bằng `cargo install --locked` từ đúng revision `eda212665a35cd01c188121e759de282728238d5` (trùng với commit trên `ptaranat/zeromem`). Model `Xenova/bge-small-en-v1.5` ở đúng revision `ea104dacec62c0de699686887e3f920caeb4f3e3`, và 5 file khớp sha256 với `harness/zeromem/zeromem-lock.json`. Lệnh `zeromem_stats` qua mcp báo `embedder: bge-small-en-v1.5` và `embedder_is_fallback: false`.

Hai phát hiện từ việc kiểm chứng cần đưa vào thiết kế. Thứ nhất, lệnh CLI `zm query` và `zm ingest` tải model vào thư mục tạm của hệ điều hành (`$TMPDIR/zeromem-models`), còn `zm mcp` và `zm hook` dùng `<home>/models`. Thứ hai, khi không tải được model, zeromem rơi về embedder hash mà không dừng lại. Vì vậy bridge chỉ được gọi qua mcp, và trạng thái phải đọc trường `embedder_is_fallback`.

Về cách deepseek-harness làm, tích hợp zeromem nằm trên `main` (`9bb7ba9a10`) với ghi chú `.agents/notes/implemented/architecture/2026-09-30-zeromem-conversation-memory.md`. Ghi chú đó chọn store theo workspace, chỉ spool tin nhắn người dùng và câu trả lời cuối của assistant, không lưu output của tool, và gọi binary `zm` thay vì viết lại bằng TypeScript. Đề xuất này dùng các quyết định đó. Không copy code TypeScript vì package phụ thuộc runtime của DSH.

## Global constraints

- Ngân sách Stop: `_BUDGET_S = float(os.environ.get("OVERSTACK_STOP_BUDGET_S", "20"))` trong `llmwiki/.claude/hooks/stop.py:35`. Mọi việc ghi memory của Stop phải nằm trong ngân sách này, hoặc chuyển sang SessionEnd.
- Revision zeromem đã ghim: `eda212665a35cd01c188121e759de282728238d5`, crate `zeromem` phiên bản `0.3.0`, giấy phép MIT.
- Model đã ghim: `Xenova/bge-small-en-v1.5`, revision `ea104dacec62c0de699686887e3f920caeb4f3e3`. Sha256 từng file theo `harness/zeromem/zeromem-lock.json`. Không cài model nếu sha không khớp.
- Store zeromem nằm ngoài repo, quyền thư mục `0700`, không bao giờ được commit.
- Tool output và nội dung file đọc được không được đi vào store.
- Script mới phải dùng `overstack_paths.*` hoặc `hooklib.*` để đường dẫn chạy đúng ở máy khách. Không ghi cứng `llmwiki/` hoặc `harness/` (theo lint `bare_path_lint.py`).
- Trên Windows, `bootstrap.sh` đặt `PYTHONUTF8=1` và `PYTHONIOENCODING=utf-8` trước khi chạy Python.
- Fail-open: thiếu `zm`, thiếu model, timeout, schema lạ đều không được chặn phiên làm việc.
- `zm mcp` không nhận session id từ Claude Code. Bridge phải tự truyền `exclude_session`.

## Non-goals

- Không xoá mem-rank, không đổi `memory.jsonl`, không đổi format episode hiện có.
- Không đổi `events.jsonl`, `scratch-log`, `provenance-log`, `ledger.jsonl`.
- Không sửa engine archify. Không cài bản fork `macos` của archify trong đề xuất này (xem Assumptions).
- Không đẩy zeromem lên repo ngoài và không mở PR upstream trong phạm vi này.
- Không thêm dependency Python ngoài thư viện chuẩn.

## Approaches

**A. Song song với khoá config, mặc định zeromem (đã chọn).** Thêm khoá `memory.backend` với ba giá trị `zeromem` (mặc định), `mem-rank`, `both`. mem-rank giữ nguyên đường cũ. Ưu điểm: có thể so sánh hai backend trên cùng dự án, chuyển ngược về mem-rank bằng một dòng config, và memory-map vẫn có nguồn cũ. Nhược điểm: ở chế độ `both`, mỗi phiên sinh cả episode mem-rank lẫn turn zeromem, và phải chấp nhận chi phí ghi gấp đôi.

**B. Thay mem-rank bằng zeromem hoàn toàn.** Gọn hơn, một hệ duy nhất. Nhược điểm: mất chuỗi phiên `continues` và `export-okf` đang chạy được, memory-map phải viết lại hoàn toàn, và không còn đường fallback không cần binary. Không chọn vì phá các phần đang hoạt động.

**C. Dùng nguyên plugin Claude Code của zeromem (`zm hook` và `zm mcp`), không viết code.** Nhanh nhất, nhưng store mặc định là `~/.zeromem` dùng chung cho mọi project. Deepseek đã bác bỏ cách này vì trộn dữ liệu và bí mật giữa các project. Không chọn.

Chọn A vì nó giữ được mọi thứ đang chạy, và việc đổi mặc định sang zeromem chỉ là một giá trị config. Quyết định chọn zeromem làm mặc định là của người dùng, đã xác nhận ngày 03/10/2026.

## Plan

- [ ] **T1: cài và ghim zeromem.** Viết `harness/scripts/zeromem-install.sh` đọc `harness/zeromem/zeromem-lock.json`, build zm đúng revision, tải model vào `<home>/models`, kiểm sha256 từng file trước khi ghi. Chuẩn bị sẵn để chạy trên máy khác, không chỉ trên máy này.
- [ ] **T2: bridge zeromem-bridge.py.** Viết `harness/scripts/zeromem-bridge.py` gọi `zm mcp` qua JSON-RPC với các lệnh `status`, `recall <câu hỏi> --exclude-session <sid>`, `forget-session <sid>` và `stats`. Mọi lỗi đều trả về rỗng và ghi log, không raise ra hook.
- [ ] **T3: chọn backend bằng config.** Thêm khoá `memory.backend` vào config (`harness/mem-rank.config.yaml` hoặc file mới) với mặc định `zeromem`. Bộ chọn đọc config một lần lúc hook khởi động. Giá trị lạ phải báo lỗi.
- [ ] **T4: nối ghi ở Stop và SessionEnd, đọc ở SessionStart.** Sửa `llmwiki/.claude/hooks/stop.py` và `llmwiki/.claude/hooks/session_start.py` để gọi zm hook với `ZEROMEM_HOME` của project và gọi bridge recall. Phần ghi chuyển sang SessionEnd nếu p95 của Stop vượt ngân sách.
- [ ] **T5: memory-map đọc zeromem và eval golden.** Thêm `--source zeromem` vào `fdk/tools/memory-map.py`, mở `zeromem.db` ở chế độ chỉ đọc và pin schema trong test. Thêm golden cross-session vào wikieval để đo hit@k của cả hai backend.

## Requirements (FR)

- **FR-001**: Hệ thống PHẢI đọc khoá `memory.backend` và chọn zeromem khi khoá thiếu hoặc bằng `zeromem`.
- **FR-002**: Hệ thống PHẢI giữ đúng hành vi hiện tại của mem-rank khi `memory.backend` là `mem-rank`.
- **FR-003**: Hệ thống PHẢI ghi turn hội thoại vào store zeromem của project khi kết thúc phiên, qua `zm hook` với `ZEROMEM_HOME` trỏ tới store đó.
- **FR-004**: Hệ thống PHẢI recall ở đầu phiên mới và loại trừ phiên hiện tại.
- **FR-005**: Hệ thống PHẢI xoá sạch một phiên khỏi store khi người dùng yêu cầu.
- **FR-006**: Hệ thống PHẢI cung cấp `memory-map --source zeromem` ở chế độ chỉ đọc.
- **FR-007**: Hệ thống PHẢI cài zm và model đúng revision đã ghim, và từ chối ghi model nếu sha256 không khớp.

## Success criteria (SC)

- **SC-001**: Người dùng mở phiên mới trong một project và thấy lại đúng việc phiên trước đã làm, mà không phải nhắc lại.
- **SC-002**: Kết thúc phiên không làm người dùng chờ thêm. Đo bằng p95 thời gian Stop trên 20 lượt, và đạt ngân sách 20 giây.
- **SC-003**: Output của công cụ và thông tin xác thực không xuất hiện trong store. Đo bằng test có tool output chứa chuỗi bí mật giả.
- **SC-004**: Sau khi xoá một phiên, phiên đó không còn xuất hiện trong kết quả recall.

## Assumptions

- Vị trí store: `~/.overstack/zeromem/<hash-project>`, ngoài repo (default). Lý do: đúng với nguyên tắc store theo project của deepseek.
- Phạm vi ghi: ghi mọi phiên (default). Đề xuất gating theo git dirty như mem-rank được giữ làm tuỳ chọn, không phải mặc định.
- Model dùng chung một bản ở `~/.overstack/zeromem/_shared/models`, mỗi store link vào đó. Đã tải và kiểm sha256 trên máy này.
- Khung trang archify dùng preset `classic`, vì bản archify đang cài là upstream `tt-a1i` (2.16.0), không có preset `macos`. Bản fork `Rheinmir/archify` có preset `macos` chưa được cài trên máy này. Cài fork là thay đổi máy khác và cần xác nhận riêng.
- Schema của `zeromem.db` chưa được công bố là giao diện ổn định (default). Test phải pin schema và báo lỗi khi đổi.

## Agent Task Assignment

| Task | Agent (CLI) | Lý do chọn | Status |
|---|---|---|---|
| T1 cài và ghim zeromem | Claude Sonnet (phiên này) | Cần đọc lock, shell và xử lý sha256. Việc ngắn, chi phí thấp. | pending |
| T2 bridge zeromem-bridge.py | Claude Sonnet (phiên này) | Cần hiểu giao thức JSON-RPC của zm mcp và xử lý lỗi fail-open. | pending |
| T3 chọn backend bằng config | Claude Sonnet (phiên này) | Thay đổi nhỏ nhưng chạm vào đường hook. Cần đọc kỹ cấu trúc config. | pending |
| T4 nối hook Stop và SessionStart | Claude Sonnet (phiên này) | Chạm vào Stop hook nhạy cảm về ngân sách. Cần đo p95. | pending |
| T5 memory-map và eval | Claude Sonnet (phiên này) | Cần đọc schema SQLite và viết golden. Phạm vi vừa. | pending |

## Render brief

Đây là nguồn để render trang companion. Mỗi task có các bước vẽ, tag `legacy` (đã có), `add` (thêm mới), hoặc `block` (chặn), và một đoạn văn đầy đủ.

- **T1.** Bước: người dùng chạy script (add), script đọc lock (legacy), cargo build đúng rev (add), model tải và kiểm sha (add, block nếu lệch), ghi vào home (add), in trạng thái (add). Đoạn văn: đã có trong trang companion, mục T1.
- **T2.** Bước: hook gọi recall (add), bridge spawn `zm mcp` (add), zm nạp spool và tìm (legacy trong zeromem), trả JSON (add), bridge lọc phiên hiện tại (add), lỗi thì trả rỗng (block). Đoạn văn: đã có, mục T2.
- **T3.** Bước: người dùng đặt khoá (add), hook hỏi bộ chọn (add), thiếu khoá thì zeromem (add), `mem-rank` giữ đường cũ (legacy), giá trị lạ thì báo lỗi (block). Đoạn văn: đã có, mục T3.
- **T4.** Bước: Stop gửi payload (legacy), stop.py gọi zm hook với `ZEROMEM_HOME` (add), spool chỉ người dùng và assistant cuối (add), SessionStart gọi bridge (add), trả tối đa ba dòng (add). Đoạn văn: đã có, mục T4.
- **T5.** Bước: memory-map đọc memory.jsonl (legacy), mở zeromem.db chỉ đọc (add, block nếu ghi), dựng graph (legacy kiểu elaborates), eval chạy golden (add). Đoạn văn: đã có, mục T5.

## Self-review

1. **Phủ yêu cầu.** Yêu cầu của người dùng gồm: zeromem song song với mem-rank và memory-map, backend mặc định là zeromem, cài zm và model. Cả ba đều có task hoặc FR tương ứng: T1 và FR-007, T3 và FR-001, T5 và FR-006. Mem-rank giữ lại qua FR-002.
2. **Quét placeholder.** Đã rà các từ bị cấm. Không có chỗ nào còn để trống hoặc viết chung chung.
3. **Nhất quán tên.** Thống nhất gọi backend là `zeromem`, bridge là `zeromem-bridge.py`, khoá config là `memory.backend`, và store là `ZEROMEM_HOME`. Trang companion dùng cùng các tên này.

## Origin

- **Draft:** `wiki/sources/draft/031026-zeromem-parallel-backend.md`
- **Companion:** `llmwiki/html/031026-zeromem-parallel-backend-seq.html` và các spec `llmwiki/html/031026-zeromem-parallel-backend-tN.sequence.json`
- **Commit:** _(filled by `verify-before-commit`)_
- **Date promoted:** _(filled by `verify-before-commit`)_
