---
type: draft
title: "Báo cáo Task 1 — cài và ghim zeromem, kiểm sha256 model theo lock"
status: shipped
tags: [zeromem, install, sha256, harness, output-report]
timestamp: 2026-10-03
---

# Báo cáo Task 1 — cài và ghim zeromem, kiểm sha256 model theo lock

**Commit:** `06d52149` trên nhánh `merge/setup-031026` (chưa push).
**PLAN gốc:** `llmwiki/wiki/sources/draft/031026-zeromem-parallel-backend-PLAN.md`, mục Task 1.
**Thoả:** FR-007.

## Tóm tắt

Task 1 tạo script cài đặt và kiểm chứng zeromem, một test cho chế độ kiểm sha256, và một bước CI chạy test đó. Test chạy PASS 3/3 trên máy tác giả. Phần đã được chứng minh là logic kiểm sha256 của lock và cách script xử lý ba trường hợp: khớp, lệch, thiếu file. Phần chưa được chứng minh là việc cài `zm` thật và tải model thật, vì hai việc này cần rustup, mạng, và chưa được chạy.

## Phạm vi thay đổi

| File | Hành động | Ghi chú |
|------|-----------|---------|
| `harness/scripts/zeromem-install.sh` | tạo | Cài `zm` đúng revision đã ghim, tải model, kiểm sha256. Có `--verify-only DIR` chỉ kiểm sha. |
| `harness/tests/zeromem-install-test.sh` | tạo | Test chế độ `--verify-only` với lock tạm. Ba ca: khớp, lệch, thiếu file. |
| `.github/workflows/harness.yml` | sửa | Thêm step `zeromem-install-test` ngay sau step memory-map. |
| `harness/zeromem/zeromem-lock.json` | không đổi | Đã tracked từ trước, nội dung khớp PLAN. Không nằm trong commit. |

Commit không dùng `git add -A`. Index chung của worktree có staging từ phiên khác, nên commit chỉ stage đúng ba file trên.

## Cách kiểm chứng đã chạy

- **Test đỏ trước khi có script.** `bash harness/tests/zeromem-install-test.sh .` trả `0 pass, 3 fail`, rc 1, vì `zeromem-install.sh` chưa tồn tại. Đây là bước TDD đúng thứ tự PLAN yêu cầu.
- **Test xanh sau khi có script.** Cùng lệnh trả `3 pass, 0 fail`, in `PASS`, rc 0.
- **Lệnh kiểm tra không có file.** `zeromem-install.sh --verify-only /nonexistent` trả rc 1 với năm dòng `THIẾU`, đúng với hành vi mong đợi.
- **Cổng bare-path.** `bare_path_lint.py --check` báo không có nợ mới, baseline 86 file.
- **Cổng harness-lint.** `harness-lint.py --check` báo 0 drift.
- **YAML của workflow.** Đọc bằng PyYAML được, hai step cuối là `memory-map` rồi `zeromem-install`.

## Thay đổi so với PLAN

PLAN ghi `mv` snapshot lệch vào `models/rejected` và in "đã chuyển" sau đó, kể cả khi snapshot không tồn tại. Script đã sửa để chỉ `mv` khi thư mục snapshot có thật, và in thông báo đúng với từng trường hợp. Logic kiểm sha, thoát 0/1, và tên file trong lock không đổi.

## Chưa xác minh và việc còn lại

- **Chưa cài `zm` thật.** Cần `cargo install --git ... --rev eda212665a35cd01c188121e759de282728238d5 --locked zeromem`. Chưa chạy vì cần rustup và mạng.
- **Chưa xác nhận cờ `zm mcp --home`.** Script gọi `zm mcp --home "$SHARED"` để khởi động model. Cờ này chưa được đối chiếu với revision đã ghim, vì chưa tải repo upstream. Script bỏ qua lỗi của bước khởi động và chỉ in cảnh báo, nên lỗi này không chặn cài đặt, nhưng việc khởi động model thật chưa được kiểm.
- **Chưa đối chiếu sha với bản tải thật.** Năm sha trong lock chưa được so với file tải từ `Xenova/bge-small-en-v1.5` ở revision `ea104dac...`. Đây là việc phải làm trước khi tin model đã được xác minh.
- **CI chưa chạy.** Step mới chỉ chạy khi có push lên nhánh, và chưa có push nào.

## Vì sao không thêm eval wiki

Hook đề nghị thêm golden đánh giá cho phần vừa làm. Có hai lý do không làm:

- Golden truy hồi (`retrieval-eval`) đang đủ 30 golden, trùng với `HARD_CAP` trong `retrieval-eval.py`. Thêm một golden buộc phải bỏ một golden đang có, và đó là quyết định của người duy trì eval, không phải của phiên này.
- Golden wikieval cần một file đáp án ứng viên. Nếu tôi tự viết đáp án rồi chấm chính nó, kết quả không đo được gì.

Kiểm chứng thật của Task 1 là test sha256 ở trên và step CI tương ứng.

## Origin

- **Session:** `2a40433d-297d-4963-9f10-eda54df4722b`
- **Commit:** `06d52149` (nội dung), `e77a08a4` (dòng index và provenance của phiên)
- **PLAN:** `llmwiki/wiki/sources/draft/031026-zeromem-parallel-backend-PLAN.md`, Task 1
