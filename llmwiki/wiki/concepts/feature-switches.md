---
type: concept
title: "Công tắc bật/tắt harness — ba lớp guardrail, gate, feature"
tags: [feature-switch, harness, guardrail, gate, feature, config]
timestamp: 2026-10-03
---

# Công tắc bật/tắt harness — ba lớp guardrail, gate, feature

Trang này mô tả cách công tắc harness **chạy thật** hôm nay. Nguồn sự thật là code: `llmwiki/.claude/hooks/hooklib.py` (`feature_on`, `feature_enabled`), `harness/features.yaml` (danh mục), `harness/scripts/feature-switch.py` (CLI), và hai copy `evidence_terminal.py` (validator R19).

## Danh mục và nơi đọc

Mọi công tắc khai trong `harness/features.yaml`. Registry được tìm theo thứ tự: thư mục harness của dự án (`.harness/` hoặc `harness/`), rồi bản global `~/.claude/harness/harness/features.yaml`. Nếu không đọc được (thiếu file, lỗi YAML, thiếu PyYAML) thì registry rỗng và `LEGACY_ENV_FALLBACK` trong `hooklib.py` vẫn nhận ba env cũ: `OVERSTACK_WIKIGRAPH`, `OVERSTACK_GOAL_HOOK`, `OVERSTACK_EVIDENCE_TERMINAL`.

Thiếu PyYAML: hooklib in đúng một dòng stderr (`[hooklib] thiếu PyYAML — ...`), công tắc đọc từ config hay registry dùng mặc định. Guardrail vẫn bật. Vì file cục bộ và config cũng đọc bằng YAML, lúc này không tắt được gì qua file.

## Thứ tự ưu tiên

Với công tắc thường (`feature`, `gate`), `feature_on` trả kết quả theo thứ tự:

1. cờ `--feature=<id>=on|off` trong argv;
2. env `OVERSTACK_FEATURE_<ID>` (ví dụ `OVERSTACK_FEATURE_GOAL_HOOK`);
3. env cũ `legacy_env` (ví dụ `OVERSTACK_GOAL_HOOK=0`);
4. `features.local.yaml` trong thư mục overstack của dự án (`.llmwiki/` hoặc `llmwiki/`);
5. config của công tắc (`config_file` + `config_key`, ví dụ `harness/agent-trace.config.yaml`);
6. `default` do caller truyền; nếu caller không truyền thì lấy `default` của registry; nếu vẫn không có thì bật.

**Guardrail** là công tắc có `class: guardrail` hoặc id nằm trong `GUARDRAIL_FALLBACK` (`egress-guard`, `orca-guard`, `inject-scan`). Với guardrail, bước 1 đến 3 và 5 bị bỏ qua: env, cờ, config và `default` của caller đều không tắt được. Chỉ `features.local.yaml` (bước 4) tắt được guardrail, và chỉ qua CLI có `--acknowledge-guardrail`. Mặc định guardrail luôn bật. Lỗi đọc bất kỳ cũng cho guardrail bật (fail-closed); với feature thì lỗi cho `default`.

## Ba lớp

Lớp là thuộc tính `class` trong `features.yaml`. Trường `switch` trong `harness/poc-vendor-neutral/policy.yaml` cũng có ba giá trị, nhưng đó là **phân loại của rule**, không phải đường tắt rule.

- **guardrail** — `egress-guard` (chặn egress, hook `pre_tool_use.py`), `orca-guard` (chặn lệnh Bash sai của orchestration, hook `orca_guard.py`), `inject-scan` (quét prompt injection; `consumer: null`, chưa có điểm gác trong hook). Tắt bằng `feature-switch off <id> --acknowledge-guardrail`, ghi vào `features.local.yaml`. Không có đường env hay config.
- **gate** — `evidence-terminal` (R19, validator `evidence_terminal.py`). Tắt được qua file cục bộ, cờ `--no-evidence-chain`, hoặc env cũ `OVERSTACK_EVIDENCE_TERMINAL=0|false|off` (xem giới hạn bên dưới).
- **feature** — `wikigraph`, `goal-hook`, `self-report`, `agent-trace`. Tắt tự do; mặc định của từng công tắc giữ nguyên.

Trong `policy.yaml`: R1 (no-write-raw) và R14 (patterns-protected) có `switch: guardrail`, 20 rule còn lại có `switch: gate`. Không có code nào đọc trường này để tắt rule. Rule là bất biến: không rule nào bị xoá hay bị tắt bởi công tắc.

## Tắt tường minh và nhật ký

- **Hook** (`feature_enabled`): khi tắt tường minh (tầng khác `mặc định`), in đúng một dòng `[harness] <id> TẮT — nguồn: <tầng>` ra stderr. Khi tắt do mặc định thì im. Hook **không** ghi `metrics/feature-switch.jsonl`.
- **CLI** (`feature-switch on|off`): in stderr khi tắt, và ghi một dòng vào `harness/metrics/feature-switch.jsonl` (`by: cli`) cho mỗi lần bật hoặc tắt.
- **Validator R19**: khi tắt, in `[R19 evidence-terminal] DANG TAT boi <tầng>` ra stderr và ghi `feature-switch.jsonl` (`by: validator`).

## Lệnh

```
python3 harness/scripts/feature-switch.py list
python3 harness/scripts/feature-switch.py status <id>
python3 harness/scripts/feature-switch.py on <id>
python3 harness/scripts/feature-switch.py off <id> [--acknowledge-guardrail]
```

- `off` bị từ chối (rc 2) khi công tắc có `consumer: null` (`self-report`, `inject-scan`), vì tắt sẽ không có tác dụng.
- `off` guardrail bị từ chối (rc 2) nếu thiếu `--acknowledge-guardrail`.
- `on` và `off` của `feature` và `gate` ghi `features.local.yaml` (cục bộ, không commit) qua ghi nguyên tử.
- `agent-trace` không ghi file cục bộ: CLI gọi `harness/scripts/agent-trace.py on|off`, công tắc thật nằm ở `harness/agent-trace.config.yaml` (`enabled`). Mặc định TẮT khi không có config.

## Từng công tắc hôm nay

| id | lớp | mặc định | nơi gác | ghi chú |
|---|---|---|---|---|
| `wikigraph` | feature | theo stamp | `stop.py` (vẽ graph), `session_start.py` (nhắc) | tắt → không vẽ graph ở Stop, không nhắc ở SessionStart. **Không** tắt bộ nhớ thứ cấp (scratch-log, provenance, memory-map, episode) — bộ nhớ thứ cấp bật theo `.harness-stamp` |
| `goal-hook` | feature | bật | `user_prompt_submit.py` | `OVERSTACK_GOAL_HOOK=0` tắt |
| `self-report` | feature | bật | chưa gắn | `OVERSTACK_SELF_REPORT_EVERY` là số, không phải công tắc |
| `agent-trace` | feature | tắt | `agent-trace.py` | bật/tắt qua `agent-trace.py`, không qua file cục bộ |
| `evidence-terminal` | gate | bật | validator R19 | xem giới hạn bên dưới |
| `egress-guard` | guardrail | bật | `pre_tool_use.py` | mode warn/block ở `harness/egress-guard.config.yaml` là việc khác |
| `orca-guard` | guardrail | bật | `orca_guard.py` | |
| `inject-scan` | guardrail | bật | chưa gắn | tắt bị từ chối vì chưa có điểm gác |

`wikigraph` theo stamp: `stop.py` truyền `default = is_framework or has_stamp`; `session_start.py` truyền `default=False`. CLI `feature-switch status` tự tính default theo stamp rồi truyền tường minh.

## Giới hạn đã biết

- **Validator R19 chưa nhận `OVERSTACK_FEATURE_EVIDENCE_TERMINAL`.** Validator giữ `load_cfg` cũ (đọc qua `bnal_config` khi có, rồi `harness/evidence-terminal.config.yaml`), thêm lớp `features.local.yaml` thắng config. Thứ tự thật trong validator: cờ `--no-evidence-chain` > env cũ `OVERSTACK_EVIDENCE_TERMINAL` > `features.local.yaml` > config. Env `=1` không thắng `enabled: false` trong config.
- Validator đọc `features.local.yaml` chỉ nhận bool hoặc chuỗi `on`/`off`; `hooklib` nhận thêm `1/0/yes/no`.
- Hook không ghi nhật ký tắt; chỉ CLI và validator ghi `feature-switch.jsonl`.
- Trường `switch` của policy chỉ được test nhất quán kiểm (`harness/tests/feature-switch-consistency-test.sh`), chưa có cơ chế tắt rule.

## Kiểm

- `harness/tests/feature-switch-test.sh` — 22 ca ma trận `feature_on`.
- `harness/tests/feature-switch-cli-test.sh` — 7 ca CLI.
- `harness/tests/feature-switch-consistency-test.sh` — hai copy `evidence_terminal.py` giống hệt; mọi rule có `switch` hợp lệ; đúng hai guardrail là R1 và R14; mọi id trong `GUARDRAIL_FALLBACK` là `class: guardrail` trong `features.yaml`. Chạy trong `.github/workflows/harness.yml`.

## Origin
- **SPEC:** `wiki/sources/draft/031026-harness-feature-switches.md`
- **PLAN:** `wiki/sources/draft/031026-harness-feature-switches-PLAN.md` (PLAN lệch code ở một số chi tiết; trang này theo code)
