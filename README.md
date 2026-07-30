# overstack — the self-disciplined AI-agent framework

**overstack** là một lớp khung (*a stack you put over your project*) biến AI Agent (Claude Code · opencode · Antigravity · Cursor…) thành một **cộng sự kỹ thuật tự-kỷ-luật**: có trí nhớ (nền tri thức `llmwiki/`), có nguyên tắc không thể phá (**guardrail** tất định chặn agent làm bậy, 0 token), có tay nghề đóng gói sẵn (skills), biết điều phối nhiều agent (Orca), và giữ được lịch sử thí nghiệm (**commit-DAG** local, không cần server).

> Nhánh làm việc chính: **`main`**.

## ⚡ Cài / update — 1 dòng (cả 3 trụ)

Chạy trong thư mục gốc dự án của bạn — **1 lệnh lo trọn harness + skills + llmwiki**, khỏi nhớ cờ.

**Cách 1 — dán cho Agent** (agent tự cài rồi tự kiểm tra mọi thứ đã đúng chỗ):

```
chạy curl -fsSL https://raw.githubusercontent.com/dragonwar000/stackoverflow/main/harness/poc-vendor-neutral/bootstrap.sh | bash và kiểm tra xem mọi thứ đã ở đúng chỗ chưa
```

**Cách 2 — chạy thẳng trong terminal:**

```bash
curl -fsSL https://raw.githubusercontent.com/dragonwar000/stackoverflow/main/harness/poc-vendor-neutral/bootstrap.sh | bash
```

Mặc định cài/update **cả 3 trụ**: **Harness** (validator tất định vendor-neutral — chặn ghi `raw/`, ép wiki có `## Origin`… qua hook native + CI làm sàn) · **Skills** (global `~/.claude/skills`) · **llmwiki** (khung wiki). Cuối lần chạy in **bảng trạng thái 3 trụ**. Cờ: `--harness-only` · `--clean` · `uninstall`.

Cài từ **một fork khác** (hoặc một nhánh khác) — gói sẵn cả bốn biến nguồn, khỏi nhớ:

```bash
curl -fsSL https://raw.githubusercontent.com/dragonwar000/stackoverflow/main/harness/poc-vendor-neutral/bootstrap-fork.sh \
  | FORK_OWNER=<owner> FORK_REPO=<repo> FORK_REF=<ref> bash
```

Tự bảo trì về sau (cập nhật + trả nợ wiki + refresh bản đồ năng lực + health-check trong một lệnh): gọi skill **`/harness-update`**.

## 📖 Tài liệu chính thức (cho người đọc)

Mở trực tiếp file self-contained — **đi theo dự án khi bạn cài** (không cần mạng, không build):

**[`llmwiki/html/overstack.html`](llmwiki/html/overstack.html)** — bắt đầu ở **Quickstart** (chạy được trong 2 phút), rồi hàng chục tab đi sâu: cài đặt · ba trụ (wiki / harness / skills) · workflow propose→gate→dispatch · Orca · build-now-adapt-later · eval/council/loop · tự bảo trì · FDK · và ★ *dev một cái mới thì cần update gì cho hợp lệ*.

Trang này **sinh bằng code** (`fdk/tools/build-overstack-docs.py`) nên bảng skill/rule luôn khớp đĩa. Bản máy-đọc của bản đồ năng lực: `fdk/CAPABILITIES.md`.

## 🧪 Vòng thí nghiệm có kỷ luật

Bản này bổ sung một lớp dành cho công việc *có thể đo được*: vòng lặp giữ đúng cái tốt hơn, đồ thị tri thức trích dẫn được, và một sổ lịch sử thí nghiệm sống bằng chính git.

| Năng lực | Gọi bằng | Nó giải gì |
|---|---|---|
| **Ratchet loop** | `loop-runner.py run --metric-cmd … --direction max` | Vòng lặp không chỉ *dừng đúng lúc* mà còn *giữ cái tốt hơn và trả lại cái tệ hơn* — keep/revert bằng `git`, mỗi vòng ghi một `Trial{commit, score, status}` |
| **Edge ID cho wiki** | `wiki-graph.py cite <trang>` · `edge <eid>` | Cạnh trong đồ thị wiki có định danh ổn định, nên câu trả lời **trích dẫn được đường đi**, không chỉ trỏ trang |
| **Evidence trong `/query`** | skill `/query` | Mỗi câu trả lời đính mục `## Evidence` liệt kê `eid` của cạnh thật sự chống lưng kết luận; không có cạnh thì khai thẳng `none` thay vì bịa |
| **Cổng grounding** | `grounding-check.py --check` | Verdict của evaluator phải theo schema `{decision, claim, reason, required_evidence[]}` — `"nhìn ổn"` là **không hợp lệ** với máy |
| **Trần độ phức tạp** | `token-budget.py` | Ngoài token và tiền, cap thêm model calls · sub-agents · concurrent workers · graph writes |
| **Sổ giả thuyết đã bỏ** | `provenance-log.py post-hypothesis` · `read-hypotheses` | Ý tưởng bị loại vẫn tra cứu được, nên agent sau không thử lại đúng cái agent trước đã thử hỏng |
| **Commit-DAG hub (local)** | `hub.py push · children · leaves · lineage` | Giữ nhiều nhánh thí nghiệm sống song song bằng `refs/hub/*` + `git notes` — **không cần server**, và thí nghiệm đã bỏ vẫn sống sót qua `git gc` |

Hub **mặc định TẮT** và gỡ được sạch theo ba tầng (tắt bằng cờ · xoá dữ liệu bằng `hub.py purge --yes` · gỡ code bằng `git revert`). `loop-runner` nạp hub **động theo đường dẫn**, không import tĩnh — xoá `hub.py` đi thì mọi thứ vẫn chạy. Chi tiết: [`llmwiki/wiki/concepts/commit-dag-hub.md`](llmwiki/wiki/concepts/commit-dag-hub.md).

## 🏗️ Dựng dự án mới — dán 1 prompt

Không copy folder, không feed từng file: mở agent ở thư mục gốc dự án mới rồi **dán nội dung [`00-New-Project.md`](00-New-Project.md)**. Agent tự cài overstack → kickoff (hỏi 3 câu) → dựng knowledge base → scaffold MVP, dừng hỏi đúng lúc cần.

Chi tiết + bản từng pha (`01`/`02`/`03`): [`setup.md`](setup.md). Cài bộ skills: `npx skills add dragonwar000/stackoverflow#main --global --all`.

## 📂 Cấu trúc

| Thư mục / file | Là gì |
|---|---|
| `llmwiki/` | **Trụ tri thức** (khuôn per-project). `wiki/` = khung wiki dự án (concepts/entities/sources/adr/draft), `skills/` (mirror), rules (`CLAUDE.md`/`AGENT.md`), `html/overstack.html` (docs). *Wiki RIÊNG của framework ở `fdk/wiki/` — ADR-008.* |
| `harness/` | **Trụ guardrail.** `validators/` + `scripts/` (install, fdk-gate, loop-runner, hub, grounding-check, token-budget, provenance-log, council/eval…). `poc-vendor-neutral/` = lõi CLI vendor-neutral + installer 1-dòng (`bootstrap.sh`, `bootstrap-fork.sh`) |
| `harness/tests/` | Test tất định của chính framework — gồm 7 bộ `ge-*` cho lớp thí nghiệm ở trên (tích hợp · hồi quy · kill-switch · travel · reachability · acceptance · mục đích) |
| `skills/` | **Trụ kỹ năng** — mỗi `SKILL.md` gọi bằng `/tên`; canonical, mirror sang `llmwiki/skills/` |
| `fdk/` | **Framework Dev Kit** — đồ nghề phát triển CHÍNH overstack + **`wiki/`** (wiki RIÊNG của framework: ADR-001..010, concepts harness/fdk, decisions), `CAPABILITIES.md`, `tools/`. Không travel xuống dự án (ADR-004/008) |
| `00–03-*.md`, `setup.md` | Prompt dựng dự án mới — **bắt đầu ở `00-New-Project.md`** (1 lần dán) |
| `.github/workflows/harness.yml` | CI: validator + self-test mỗi PR |

## 🛠️ Phát triển chính overstack

Gọi skill **`/fdk`** (front-door on-demand: pre-flight + inventory live). Định-nghĩa-hoàn-thành cho mọi thay đổi: `python3 harness/scripts/fdk-gate.py` — **21 step**, gồm một step chạy trọn 7 bộ test `ge-*`. Cổng sức khoẻ tổng: `python3 fdk/tools/medic.py`. Quyết định kiến trúc: `fdk/wiki/sources/adr/` — gate **R13** ép `decisions.md` (architecture) phải ref ADR, cho edit + xóa khi đã bị đè.

Trước khi công bố một bản có năng lực mới: skill **`/fdk-uat`** — dựng dự án TRỐNG, cài bằng `curl` từ raw của chính nhánh đó, kiểm năng lực mới có thật sự tới tay không. `medic` và `fresh-install-smoke` cài từ working-tree nên **không** chứng minh được đường remote.

- Cài thủ công / gỡ / cài từ fork / chi tiết: [`harness/poc-vendor-neutral/README.md`](harness/poc-vendor-neutral/README.md)
- Bản tải về (offline): [Releases](../../releases)

## Nguồn gốc

Repo này là bản độc lập dựng từ nhánh `graph-engineering` của [`dragonwar000/setup`](https://github.com/dragonwar000/setup) (fork của `Rheinmir/setup`). Lớp thí nghiệm ở mục 🧪 chưng cất từ *Graph Engineering: The Karpathy Loop, Improved 1000x by Itself — The Anthropic Playbook* (07/2026), cùng phần đối chiếu 67 mục trong `llmwiki/wiki/sources/draft/290726-spec-vs-overstack.md`.
