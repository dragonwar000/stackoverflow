---
type: draft
title: "Công tắc bật/tắt các chức năng harness"
status: proposed
tags: [harness, switch, config, hooks, propose]
timestamp: 2026-10-03
---

# 031026-harness-feature-switches

**Status:** proposed

**Sequence diagram:** [trang companion theo task](../../../html/031026-harness-feature-switches-seq.html)

## What

Đưa mọi công tắc bật/tắt của harness về một danh mục duy nhất và một cách đọc duy nhất. Người dùng bật hoặc tắt một chức năng cho một dự án, cho một lần chạy, hoặc cho cả repo, bằng một lệnh, không cần sửa `settings.json` và không cần nhớ tên biến môi trường. Hành vi mặc định của mọi chức năng hiện có giữ nguyên.

## Context

**Hiện trạng đã khảo sát trên code.** Mỗi cơ chế có một cách tắt riêng và không nhất quán:

| Cơ chế | Cách tắt hiện có | Bằng chứng |
|---|---|---|
| Hook toàn cục | Đăng ký trong `~/.claude/settings.json`, chỉ chạy ở dự án có `.llmwiki/.harness-stamp`. Tắt một hook = gỡ entry bằng tay. Tắt cả dự án = xoá stamp. | `llmwiki/.claude/hooks/hooklib.py:154`; `session_start.py:346` |
| Rule policy | 22 rule trong `harness/policy.yaml`. Không rule nào có khoá `enabled`. | khảo sát khoá của 22 rule: `id, name, validator, statement, enforce_at, applies_to, scope, note` |
| Khoá `enabled:` trong config | Chỉ 2 file: `harness/agent-trace.config.yaml:9` và `harness/evidence-terminal.config.yaml:5`. | grep `^enabled:` |
| Biến môi trường | `OVERSTACK_EVIDENCE_TERMINAL=0` (tắt, có ba tầng cùng cờ `--no-evidence-chain`); `OVERSTACK_GOAL_HOOK=0` (tắt, mặc định bật); `OVERSTACK_WIKIGRAPH=1` (bật). Phần còn lại là ngưỡng số: `OVERSTACK_STOP_BUDGET_S`, `OVERSTACK_DRAFT_THRESHOLD`, `OVERSTACK_SELF_REPORT_EVERY`, `OVERSTACK_TOUCHED_*`. | grep `OVERSTACK_` trong hooks và scripts |
| Cài đặt | `bootstrap.sh --harness-only`, `--no-graph`, `--no-verify`; `install-harness.sh --global`; `uninstall.sh`. Đây là công tắc lúc cài, không có công tắc mềm lúc chạy. | `harness/poc-vendor-neutral/bootstrap.sh:10-14`; `harness/poc-vendor-neutral/uninstall.sh` |
| Skill | Chưa thấy công tắc mềm nào. Theo khảo sát chỉ có cài và gỡ qua installer. | khảo sát `harness/scripts/install-harness.sh` |

**Một cờ đang bị đọc theo hai nghĩa.** `OVERSTACK_WIKIGRAPH` được `stop.py:117` đọc như sau: bật khi có stamp, hoặc khi `env == "1"`. Cùng cờ đó, `session_start.py:289` chỉ nhắc khi `env == "1"`. Hệ quả: ở dự án đã có stamp, graph vẫn được regen nhưng không có nhắc, và không có cách nào tắt graph bằng env, vì `env=0` không được đọc ở đường Stop. Muốn tắt phải xoá stamp, tức tắt luôn toàn bộ harness của dự án.

**Tiền lệ đáng giữ.** Công tắc ba tầng của bộ kiểm evidence-terminal (cờ lần chạy, rồi env theo máy, rồi config theo repo, theo thứ tự hẹp tới rộng) và nguyên tắc in một dòng ra stderr mỗi khi tắt được ghi rõ trong `llmwiki/wiki/concepts/evidence-terminal-chain.md:172-188`. Nguyên tắc đó là: tắt phải nhìn thấy được, vì một cơ chế im lặng lúc không chạy sẽ bị nhầm là đang chạy. Nguyên tắc nguồn chân lý của policy được ghi trong `fdk/wiki/decisions.md` (dòng ADR-001 policy-as-source-of-truth, và `llmwiki/wiki/concepts/rule-registry.md`). Mẫu opt-in dự án được ghi trong `fdk/wiki/sources/adr/ADR-004-framework-dev-context-opt-in.md`. Danh mục cơ chế đã có sẵn: `harness/mechanisms.yaml`, 28 mục, mỗi mục có `kind` (rule, hook, skill, tool) và `live_probe`.

Vậy có sẵn một danh mục (`mechanisms.yaml`) và một mẫu công tắc (evidence-terminal). Việc còn thiếu là một cách đọc thống nhất và một lệnh để đổi.

## Global constraints

- Mọi chức năng mặc định giữ đúng hành vi hiện tại. Không đổi giá trị mặc định của bất kỳ công tắc nào trong phạm vi này.
- Hook là fail-open: lỗi đọc công tắc không được chặn phiên làm việc. Ngoại lệ là guardrail (xem FR-004): lỗi đọc công tắc guardrail phải giữ guardrail BẬT.
- Mọi lần tắt một chức năng phải in một dòng ra stderr nêu rõ chức năng và tầng đã tắt nó.
- Không xoá rule nào khỏi `harness/policy.yaml`. Rule là bất biến. Đề xuất này chỉ thêm đường tắt có kiểm soát cho chức năng, không cho rule.
- Đường dẫn trong script mới phải dùng `overstack_paths.*` hoặc `hooklib.*`. Không ghi cứng `llmwiki/` hoặc `harness/` (lint `bare_path_lint.py`).
- Không dùng `git add -A` hoặc `git add .`. Stage theo danh sách file cụ thể (hook `P1 no-bulk-stage`).
- Trên Windows, Python chạy với `PYTHONUTF8=1`.
- File HTML mới phải tự chứa, không request ra ngoài.

## Non-goals

- Không bật hoặc tắt skill lúc chạy. Skill vẫn cài và gỡ qua installer.
- Không đổi ngưỡng số (`OVERSTACK_STOP_BUDGET_S`, `OVERSTACK_DRAFT_THRESHOLD`, `OVERSTACK_SELF_REPORT_EVERY`, `OVERSTACK_TOUCHED_*`). Chúng là tham số, không phải công tắc.
- Không gỡ hay đổi cơ chế cài đặt của `bootstrap.sh` và `install-harness.sh`.
- Không xoá hay sửa nội dung rule trong `policy.yaml`. Rule vẫn bất biến. Các gate được nhóm theo lớp, và mỗi gate có một công tắc theo id trong `features.yaml`.
- Không dùng công tắc để vượt qua kiểm tra bảo mật. Guardrail nằm trong danh sách riêng (FR-004).

## Approaches

**A. Danh mục công tắc `harness/features.yaml` và một bộ đọc chung `hooklib.feature_on` (đã chọn).** Mỗi chức năng khai một mục: `id`, `scope`, `default`, `legacy_env`, `config_key`, `guardrail`. Bộ đọc áp đúng một thứ tự ưu tiên: cờ lần chạy, rồi env `OVERSTACK_FEATURE_<ID>`, rồi file cục bộ `.llmwiki/features.local.yaml` (không commit), rồi `harness/features.yaml`, rồi mặc định. Ưu điểm: một nguồn duy nhất, mọi hook đọc giống nhau, và tương thích ngược với biến môi trường cũ. Nhược điểm: phải sửa từng hook một, và cần một bước migrate có kiểm thử.

**B. Chỉ viết tài liệu cho các biến môi trường hiện có.** Rẻ nhất, không sửa code. Nhưng giữ nguyên hai nghĩa của `OVERSTACK_WIKIGRAPH` và không có cách tắt thống nhất. Không chọn.

**C. Gỡ entry hook bằng script trong `settings.json`.** Đụng vào file do installer quản lý, dễ lệch khi cài lại, và không cho tắt ở mức chức năng bên trong một hook. Không chọn.

Chọn A vì nó sửa đúng chỗ bị lệch (hai nghĩa của một cờ, và cách tắt rải rác) mà không đổi hành vi mặc định.

## Plan

- [ ] **T1: danh mục và bộ đọc chung.** Tạo `harness/features.yaml` liệt kê mọi công tắc hiện có, kèm lớp `switch`, và thêm `feature_on(root, id)` vào `llmwiki/.claude/hooks/hooklib.py`. Thứ tự ưu tiên và quy tắc fail-closed của lớp `guardrail` được cài đặt ở đây.
- [ ] **T2: lệnh `feature-switch`.** Tạo `harness/scripts/feature-switch.py` với các lệnh `list`, `status <id>`, `on <id>`, `off <id>`. Lệnh `status` in giá trị hiệu lực và tầng nguồn của nó. Lệnh `off` với guardrail phải có cờ `--acknowledge-guardrail`, và mọi lần tắt đều được ghi vào `harness/metrics/feature-switch.jsonl`.
- [ ] **T3: chuyển các cờ hiện có sang bộ đọc chung.** Sửa `stop.py`, `session_start.py`, `user_prompt_submit.py`, `hooklib.py` và hai config có `enabled:` để đọc qua `feature_on`. Đồng thời giải quyết hai nghĩa của `OVERSTACK_WIKIGRAPH` bằng một quy tắc duy nhất, giữ giá trị mặc định hiện tại.
- [ ] **T4: kiểm thử, tài liệu, và đăng ký.** Thêm `harness/tests/feature-switch-test.sh` kiểm ma trận thứ tự ưu tiên, guardrail fail-closed, và dòng stderr khi tắt. Đăng ký mục mới vào `harness/mechanisms.yaml` và viết trang concept `feature-switches`.

## Requirements (FR)

- **FR-001**: Hệ thống PHẢI liệt kê mọi công tắc hiện có trong `harness/features.yaml`, kèm mặc định và biến môi trường cũ tương ứng.
- **FR-002**: Hệ thống PHẢI đọc công tắc theo đúng thứ tự: cờ lần chạy, env `OVERSTACK_FEATURE_<ID>`, file cục bộ, file repo, mặc định.
- **FR-003**: Người dùng PHẢI bật hoặc tắt một chức năng cho một dự án bằng một lệnh, mà không sửa `settings.json` và không sửa file đã commit.
- **FR-004**: Lớp `guardrail` PHẢI giữ bật khi lỗi đọc công tắc. Tắt guardrail chỉ qua `feature-switch off <id> --acknowledge-guardrail`, KHÔNG qua biến môi trường hay config, và PHẢI in stderr.
- **FR-005**: Mọi chức năng hiện có PHẢI giữ đúng hành vi mặc định sau khi migrate.
- **FR-006**: Các biến môi trường cũ (`OVERSTACK_EVIDENCE_TERMINAL`, `OVERSTACK_GOAL_HOOK`, `OVERSTACK_WIKIGRAPH`) PHẢI tiếp tục có hiệu lực như trước.
- **FR-007**: Lệnh `status` PHẢI in giá trị hiệu lực và tầng nguồn của giá trị đó.
- **FR-008**: Lớp `gate` (R2, R3, R7, R9, R18, R19, R20, R22 và các rule khác được phân lớp `gate`) PHẢI giữ đường tắt bằng biến môi trường và config như hôm nay. Mỗi lần tắt PHẢI in stderr và ghi một dòng vào `harness/metrics/feature-switch.jsonl`. Không cần cờ xác nhận.
- **FR-009**: Mỗi rule trong `harness/policy.yaml` PHẢI khai trường `switch` nhận đúng một trong ba giá trị `guardrail`, `gate`, `feature`.

## Success criteria (SC)

- **SC-001**: Người dùng tắt được một chức năng trong một dự án bằng một lệnh, và sau đó chức năng đó không chạy ở phiên tiếp theo. Kiểm bằng test trên dự án tạm.
- **SC-002**: Không có hành vi mặc định nào đổi sau migrate. Đo bằng toàn bộ test hiện có của harness đều vẫn xanh.
- **SC-003**: Không có lần tắt nào im lặng. Mỗi lần tắt đều có một dòng stderr, kiểm bằng test.
- **SC-004**: Không có guardrail nào tắt được mà không có cờ xác nhận. Kiểm bằng test ma trận.
- **SC-005**: Mọi rule trong `harness/policy.yaml` đều có trường `switch` hợp lệ. Kiểm bằng test đọc policy.

## Assumptions

- Phân lớp (default, người duyệt đã chấp thuận 03/10/2026, R1 và R14 xác nhận là `guardrail`): `guardrail` = R1 no-write-raw, R14 patterns-protected, `egress-guard`, `inject-scan`, `orca_guard`. `gate` = R2, R3, R7, R9, R18, R19, R20, R22, và các rule còn lại đánh dấu `gate` trong bước T3. `feature` = orientation, wiki-graph, goal-hook, agent-trace, self-report.
- R19 là `gate`, không phải `guardrail`: nó kiểm chất lượng nội dung tài liệu, không phải nền tảng bảo mật. Tắt R19 bằng `OVERSTACK_EVIDENCE_TERMINAL=0` hoặc `enabled: false` vẫn được giữ (FR-008) và phải ghi stderr và nhật ký.
- `evidence_leaf.py` là engine dùng chung với `grounding-check.py`. Công tắc chỉ tắt cổng R19, không tắt engine.
- File công tắc cục bộ là `.llmwiki/features.local.yaml`, không commit, đặt trong thư mục overstack của dự án (default).
- Cờ lần chạy là tham số `--feature <id>=<on|off>` của script chạy hook, chỉ có hiệu lực trong một lần chạy (default).
- Các biến `OVERSTACK_EVIDENCE_TERMINAL`, `OVERSTACK_GOAL_HOOK`, `OVERSTACK_WIKIGRAPH` được giữ làm alias của công tắc tương ứng. Giá trị mặc định là giá trị hiện tại trong code (default).
- Quy tắc thống nhất cho `OVERSTACK_WIKIGRAPH` là: graph bật khi có stamp hoặc khi env là `1`, và nhắc khi graph bật. Quy tắc này khớp với hành vi `stop.py` hiện tại (default, cần xác nhận).

## Agent Task Assignment

| Task | Agent (CLI) | Lý do chọn | Status |
|---|---|---|---|
| T1 danh mục và bộ đọc chung | Claude Sonnet (phiên này) | Thiết kế thứ tự ưu tiên và quy tắc fail-closed, cần đọc hooklib. | pending |
| T2 lệnh feature-switch | Claude Sonnet (phiên này) | Giao diện CLI và ghi nhật ký, phạm vi vừa. | pending |
| T3 migrate các cờ hiện có | Claude Sonnet (phiên này) | Chạm vào Stop và SessionStart, cần giữ mặc định. | pending |
| T4 kiểm thử, tài liệu, đăng ký | Claude Sonnet (phiên này) | Ma trận kiểm thử và cập nhật mechanisms. | pending |

## Render brief

- **T1.** Bước: đọc danh mục (add), `feature_on` áp thứ tự ưu tiên (add), guardrail khi lỗi đọc thì giữ bật (add, block nếu tắt), feature khi lỗi thì dùng mặc định (legacy). Đoạn văn: đọc được trong trang companion, mục T1.
- **T2.** Bước: người dùng chạy `off` (add), script kiểm guardrail và cờ xác nhận (add, block nếu thiếu cờ), ghi file cục bộ (add), ghi nhật ký (add), in dòng stderr (add). Đoạn văn: mục T2.
- **T3.** Bước: hook gọi `feature_on` thay cho env trực tiếp (add), env cũ vẫn được đọc (legacy), quy tắc WIKIGRAPH thống nhất (add). Đoạn văn: mục T3.
- **T4.** Bước: ma trận kiểm thử (add), đăng ký mechanisms (add), trang concept (add). Đoạn văn: mục T4.

## Self-review

1. **Phủ yêu cầu.** FR-001 → T1. FR-002 → T1. FR-003 → T2. FR-004 → T1 và T2. FR-005 → T3 và T4. FR-006 → T3. FR-007 → T2. Không yêu cầu nào bị bỏ rơi.
2. **Quét placeholder.** Đã rà các từ bị cấm. Không có chỗ nào để trống.
3. **Nhất quán tên.** Thống nhất gọi bộ đọc là `feature_on`, danh mục là `harness/features.yaml`, lệnh là `feature-switch`, file cục bộ là `.llmwiki/features.local.yaml`.

## Origin

- **Draft:** `wiki/sources/draft/031026-harness-feature-switches.md`
- **Companion:** `llmwiki/html/031026-harness-feature-switches-seq.html` và các spec `llmwiki/html/031026-harness-feature-switches-tN.sequence.json`
- **Commit:** _(filled by `verify-before-commit`)_
- **Date promoted:** _(filled by `verify-before-commit`)_
