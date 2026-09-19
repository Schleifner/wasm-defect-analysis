# 当前分析工作流

本文描述仓库当前实际执行的 AI 辅助缺陷分析流程。AI 负责按固定格式写报告，人类直接阅读证据并给出最终判断。

## 总览

```mermaid
flowchart TD
  A[选择目标和范围] --> B[new_run.py 快照当前 Prompt 并创建 Run]
    B --> C[AI 在固定提交上分析]
    C --> D[填写 report.md 和 artifacts]
    D --> E[人类直接阅读和判断]
    E --> F[总结误报、漏报和证据缺口]
    F --> G[更新唯一 Prompt 并创建下一次 Run]
    E --> H[人工结论进入监督数据集]
```

工作流只有两个核心产物：

- `manifest.json`：记录本轮实验配置和精确的上游提交。
- `report.md`：AI 的格式化分析和人类的最终评价写在同一份 Markdown 中。

不再需要额外的 Python 校验、JSON review 或自动评分步骤。

## 1. 准备上游版本

仓库管理两个顶层 submodule：

- `upstream/warpo` 跟踪 `main`；
- `upstream/wasm-compiler` 跟踪 `develop`。

初始化：

```bash
git submodule update --init upstream/warpo upstream/wasm-compiler
```

需要主动更新到远端最新提交时：

```bash
./scripts/update_upstreams.sh
```

不要从父仓库执行递归 submodule 初始化。每次 Run 都保存精确提交，所以更新上游不会改变旧实验的上下文。

## 2. 创建一次 Run

先确定单一、可审计的分析范围：

```bash
python3 scripts/new_run.py \
  --run-id run-002-warpo-parser \
  --model <provider/model> \
  --agent <agent-or-harness> \
  --target warpo \
  --scope "frontend parser diagnostics" \
  --temperature 0 \
  --budget "60 minutes"
```

脚本生成：

```text
runs/run-002-warpo-parser/
  manifest.json
  prompt.md
  report.md
  artifacts/
```

- `manifest.json` 固定模型、参数、范围、Prompt 哈希和上游提交。
- `prompt.md` 是唯一源 Prompt `prompts/defect-discovery.md` 在本轮创建时的快照。
- `report.md` 是 AI 输出和人工评价的共同载体。
- `artifacts/` 保存最小复现输入和精简日志。

仓库只维护 `prompts/defect-discovery.md` 这一个源 Prompt。Run 生成器总是快照它的当前内容，并在 manifest 中记录 SHA-256。旧 Run 使用各自目录中的 `prompt.md` 保留当时内容，因此后续迭代源 Prompt 不会改变历史实验。

Run ID 不复用。修改 Prompt、模型配置、范围或重试实验时都创建新 Run。

## 3. AI 分析

让分析 agent 读取本轮的 `manifest.json` 和 `prompt.md`，只分析声明的目标与范围。发现阶段不修改两个上游 submodule。

AI 直接填写 `report.md`，每个候选至少回答：

1. 哪个公开输入能够到达这段代码？
2. 实际行为违反了什么规范、设计或可验证语义？
3. 在固定基线上执行了什么命令，观察到了什么？
4. 独立 oracle 是什么？
5. 邻近的反例或控制用例是否通过？

生产者可达性仍然是候选进入报告前的硬性条件，但不再作为单独字段重复填写。AI 已经判断为 `reject` 的假设不写进 Candidate Findings；只有复现成功的 `accept`、`downgrade`，以及确实缺少决定性证据的 `defer` 可以保留给人工复核。

每个候选必须使用独立、最小化的源文件，不要把多个 bug 放进一个 AS 文件或多导出 harness。复现输入、精确命令、退出码和关键输出合并写在同一个“Reproduction”条目中。

AI recommendation 之外还要给出独立的价值判断：

- `high`：普通、语义正确的输入发生崩溃、误编译、无效输出或明确的求值语义错误；
- `low`：主要依赖极端边界值、明显错误或不合理的用户代码、狭窄的健壮性问题；
- `unknown`：仅用于证据不足的 `defer`。

Warpo 内部 pass 的手写 WAT/IR 不自动代表产品缺陷，必须证明 Warpo frontend 能产生该状态。wasm-compiler 的公开输入是受支持的合法 Wasm，因此由标准工具组装的合法 WAT 可以作为输入。

如果没有发现问题，AI 应明确写“未发现”；如果证据不足，写 `defer`，不要猜测。

### 3.1 Warpo 固定构建与执行入口

分析 Warpo 时先读取 `.github/skills/warpo-defect-workflow/SKILL.md`，不要每轮重新推导构建和 Node.js 运行方式。Node.js 版本必须不低于 22.4。从仓库根目录执行：

```bash
git submodule update --init upstream/warpo
cd upstream/warpo
npm ci
npm run build
cd ../..
```

`npm run build` 是稳定入口，会生成 `upstream/warpo/dist/warpo.js` 和 `upstream/warpo/build/warpo/warpo_asc`。CMake 是 npm 脚本的内部实现；除非正在诊断 `npm run build` 本身的失败，否则不要手工挑选 CMake target。

每个候选使用独立的最小 AS 源文件，然后从仓库根目录编译和执行：

```bash
node upstream/warpo/dist/warpo.js \
  runs/<run-id>/artifacts/C-001.ts \
  -o runs/<run-id>/artifacts/C-001.wasm \
  --exportRuntime
node scripts/run_warpo_wasm.mjs \
  runs/<run-id>/artifacts/C-001.wasm \
  exportedFunction \
  42 7n
```

通用 runner 提供标准的 `env.abort`，接受普通数值参数，并用 `n` 后缀表示 `i64`。它会明确拒绝未知 import；需要 WASI 或项目特定 import 时，在候选目录中创建专用 runner，不要向通用 runner 静默加入无语义的 stub。runner 只负责稳定执行，不是独立 oracle。

可用下面的命令检查整条基础设施链路，预期输出为 `add=42`：

```bash
node upstream/warpo/dist/warpo.js \
  .github/skills/warpo-defect-workflow/assets/smoke.ts \
  -o /tmp/warpo-defect-workflow-smoke.wasm \
  --exportRuntime
node scripts/run_warpo_wasm.mjs /tmp/warpo-defect-workflow-smoke.wasm add 20 22
```

### 3.2 中文分析过程记录

从一轮 discovery 开始时就在 `report.md` 的 `## 中文分析过程记录` 下持续追加公开的中文分析日志，不要等结束后再概括。按实际发生顺序简要记下：

- 当前选择的 detect 方向以及选择原因；
- 提出的可证伪假设和准备做的关键检查；
- 检查得到的关键事实，以及该事实如何让方向继续、停止或转向；
- 被否定的假设和未形成候选的方向。

完成时保留这些条目的原始顺序和表述，不要再改写成经过整理的审计或摘要。Candidate Findings 仍只收录通过 admission gate 的候选；过程日志可以保留失败方向。不要改写留给人的 `Human Review` 内容。

## 4. 人类阅读和评价

打开：

```text
runs/run-002-warpo-parser/report.md
```

直接填写报告中的“人工评价”部分：

- 最终结论：`accept` / `downgrade` / `reject` / `defer`；
- 价值：`high` / `low` / `none` / `unknown`；
- 评价和关键依据。

重点检查：

- 输入是否能由目标项目的公开入口产生；
- 行为是否真的违反规范或设计，而不是预期优化；
- 是否在固定基线复现；
- 是否有独立 oracle；
- 是否有附近的反例或控制用例。

人工判断就是本仓库的监督信号。不要运行额外脚本，也不需要把评价拆到另一个 JSON 文件。

## 5. 迭代 Prompt

根据报告中的人工评价总结：

- AI 把设计预期误判成 bug 的地方；
- AI 没有检查生产者可达性的地方；
- 复现或 oracle 不充分的地方；
- 重复发现和搜索遗漏。

同时检查报告是否把已否定的假设当作候选输出、是否把多个 bug 合并进同一个复现文件，以及是否把低价值边界问题误标成高价值。

直接更新唯一的 `prompts/defect-discovery.md`，不要再创建 `v2-*`、`v3-*` 等并行文件。修改前应确保上一轮 Run 已经创建并保存其 `prompt.md` 快照；修改后使用新 Run ID。比较前后效果时，以各 Run 的 prompt SHA-256 和快照区分 revision，并尽量保持目标范围、模型预算和采样参数一致。

`supervision/round-001` 已写入 Prompt，因此只能作为训练/回归监督。选择 Prompt revision 要使用未泄漏标签的 validation；最终泛化结果使用 holdout。

## 6. 写入监督数据集或修复

一轮人工审阅完成后，在 `supervision/<round-id>/` 中只保存 `review.md` 和 `oracle.json`。前者记录人类可读的判断和流程反馈，后者记录供 Prompt 迭代与评估使用的结构化标签。复现源码、编译产物和运行日志不复制进监督目录。

人工确认的发现只有在以下条件满足后才进入监督数据集：

1. 在记录的基线提交上稳定复现；
2. 已证明支持输入可达；
3. 复现已最小化；
4. 有独立 oracle；
5. 有邻近控制用例；
6. 已分配稳定 ID 和数据集 split。

需要修复上游时，先保留基线 Run 的证据，再在对应 submodule 内做最小修改并运行其原生测试。除非明确要推进父仓库 pin，否则不要随意更新 submodule 指针。

## 仓库工具职责

| 文件 | 职责 |
| --- | --- |
| `scripts/new_run.py` | 创建 Run，快照 Prompt、模型配置和上游提交 |
| `scripts/update_upstreams.sh` | 按声明分支更新两个上游 submodule |

本仓库不再使用 Python 做候选校验或自动评分。
