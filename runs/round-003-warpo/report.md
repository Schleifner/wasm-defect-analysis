# AI Defect Analysis Report: Warpo frontend, semantic lowering, standard-library common paths, and source-reachable optimizations; identify three distinct high-value defects excluding rounds 001 and 002

## Run Metadata

- Run ID: `round-003-warpo`
- Prompt: `defect-discovery`
- Model: `GitHub Copilot`
- Target: `warpo`
- Baseline commits: Warpo `8466a752edccaedb5de8ae3246e139a7fb71a51d`, wasm-compiler `N/A`

## Analysis Scope

- Warpo frontend expression lowering, semantic analysis, standard-library common paths,
  and source-reachable optimization behavior at commit
  `8466a752edccaedb5de8ae3246e139a7fb71a51d`.
- Excludes all candidates already investigated in rounds 001 and 002.
- Upstream source remains unmodified; discovery artifacts are isolated under this run.

## Candidate Findings

### C-001: String.replaceAll underallocates for a long replacement

- Location: `upstream/warpo/assemblyscript/std/assembly/string.ts:420-480`,
	`String#replaceAll` growth path.
- Hypothesis: replacing a short match with text longer than twice the source length grows
	the destination only once, so the replacement write exceeds the renewed string capacity.
- Root cause: when `offset + chunk + replaceLen > outSize`, the implementation performs one
	`outSize <<= 1` instead of growing to at least the required size. For a two-character source
	and ten-character replacement, capacity becomes four characters before a ten-character copy.
- Impact: an ordinary valid string replacement corrupts allocator-adjacent memory and aborts
	instead of returning the eleven-character result.
- Reproduction: `runs/round-003-warpo/artifacts/C-001.ts`; compile with
	`node upstream/warpo/dist/warpo.js runs/round-003-warpo/artifacts/C-001.ts -o runs/round-003-warpo/artifacts/C-001.wasm --exportRuntime`,
	exit `0`; run with
	`node scripts/run_warpo_wasm.mjs runs/round-003-warpo/artifacts/C-001.wasm reproduce`,
	exit `1`, output `AssemblyScript abort at 245:14 (message=0, file=480)`.
- Independent oracle: Node.js evaluation of
	`"ab".replaceAll("a", "0123456789").length` exited `0` and returned `11`.
- Negative/control case:
	`node scripts/run_warpo_wasm.mjs runs/round-003-warpo/artifacts/C-001.wasm control`
	exited `0` with `control=7` for the nearby shorter-replacement case.
- AI recommendation: `accept`
- AI value: `high`
- AI value rationale: common, semantically valid string input causes a runtime abort and an
	out-of-bounds standard-library write; no malformed or extreme argument is required.

### C-002: String.indexOf ignores start for an empty search string

- Location: `upstream/warpo/assemblyscript/std/assembly/string.ts:208-218`,
	`String#indexOf`.
- Hypothesis: `indexOf` returns zero for an empty search string before clamping and applying
	the explicit start position.
- Root cause: `if (!searchLen) return 0` precedes the `searchStart` calculation, so every empty
	search reports index zero regardless of `start`.
- Impact: valid searches silently return the wrong position, which can break parsers and text
	processing that use an empty delimiter or boundary search.
- Reproduction: `runs/round-003-warpo/artifacts/C-002.ts`; compile with
	`node upstream/warpo/dist/warpo.js runs/round-003-warpo/artifacts/C-002.ts -o runs/round-003-warpo/artifacts/C-002.wasm --exportRuntime`,
	exit `0`; run with
	`node scripts/run_warpo_wasm.mjs runs/round-003-warpo/artifacts/C-002.wasm reproduce`,
	exit `0`, output `reproduce=0`.
- Independent oracle: Node.js evaluation of `"abc".indexOf("", 2)` exited `0` and returned
	`2`; existing standard-library tests establish JavaScript-like `String#indexOf` behavior but
	cover an empty search only at the default start.
- Negative/control case:
	`node scripts/run_warpo_wasm.mjs runs/round-003-warpo/artifacts/C-002.wasm control`
	exited `0` with `control=1` for `"abc".indexOf("b", 0)`.
- AI recommendation: `accept`
- AI value: `high`
- AI value rationale: ordinary valid input produces a deterministic wrong value in a core
	string API, with no unsafe operation or exceptional boundary value.

### C-003: Map rehash makes an active iterator skip a live entry

- Location: `upstream/warpo/assemblyscript/std/assembly/map.ts:68-81` (`MapIterator#next`),
	`148-169` (`Map#set`), and `202-230` (`Map#rehash`).
- Hypothesis: after an iterator has advanced, deletion plus insertion can compact the map's
	entry array while the iterator retains its old physical index, skipping a surviving entry.
- Root cause: `MapIterator` stores an array offset `i`. `rehash` compacts all live entries into
	a new array but neither preserves their old offsets nor updates active iterators. The next call
	resumes at index one in the compacted array, skipping the live entry moved to index zero.
- Impact: mutation during supported live iteration silently omits an existing map entry and
	violates insertion-order iteration.
- Reproduction: `runs/round-003-warpo/artifacts/C-003.ts`; compile with
	`node upstream/warpo/dist/warpo.js runs/round-003-warpo/artifacts/C-003.ts -o runs/round-003-warpo/artifacts/C-003.wasm --exportRuntime`,
	exit `0`; run with
	`node scripts/run_warpo_wasm.mjs runs/round-003-warpo/artifacts/C-003.wasm reproduce`,
	exit `0`, output `reproduce=4`.
- Independent oracle: equivalent Node.js `Map` mutation exited `0` and yielded key `3`.
	Warpo's `std/map-iterator.ts` tests also require iterators to observe insertion-order behavior
	while entries are added or deleted.
- Negative/control case:
	`node scripts/run_warpo_wasm.mjs runs/round-003-warpo/artifacts/C-003.wasm control`
	exited `0` with `control=3` when the same kind of mutation does not fill the entry array and
	therefore does not invoke `rehash`.
- AI recommendation: `accept`
- AI value: `high`
- AI value rationale: a normal collection mutation pattern silently loses data during a public
	iterator workflow already exercised by upstream mutation tests.

## Human Review

<!-- Review each candidate here. No additional Python checker is required. -->
- 不要改现有的记录，在未来的人类review环节，把 Key evidence:这一栏删了，不需要它

### C-001

- Final decision: `accept`
- Value: `high`
- Review: 很明显的bug，从当前上下文就能推断出原实现是错的，没有依赖外部的对比测试如JS的对比，且很容易复现并修复，奖励
- Key evidence:

### C-002

- Final decision: `accept`
- Value: `low`
- Review: 表现的语义和JS不一致，的确是bug。原来没有测试用例覆盖这个case，但更像是不支持这种用法，没有人这么用并且没有文档或者spec说明
- Key evidence:

### C-003

- Final decision: `accept`
- Value: `high`
- Review: 很好的发现，是runtime的隐式bug，希望之后发现这种不太直观的bug时，更清晰的描述原来的实现错在哪，更加详细的介绍，并给复现用例加适当的注释
- Key evidence:

## Summary

- Reported candidates: 3. AI high-value yield: 3/3 reported candidates.
- AI recommendations: 3 `accept`, 0 `downgrade`, 0 `defer`.
- AI value ratings: 3 `high`, 0 `low`, 0 `unknown`.
- Areas searched with no findings: logical and conditional expression lowering, ordinary
	source-reachable optimization paths, typed-array reversal, and additional parser/type-system
	surfaces. Prefix/indexed unary-update issues were excluded as the same root cause as round-002
	C-001. Signed-sort overflow was reproduced but omitted in favor of higher-value findings.
	Captured-`var` loop behavior was reproduced but omitted because the AssemblyScript contract
	could not be established.
- Unresolved checks and environmental blockers: none for the three reported candidates.
- Suggested prompt or infrastructure change for the next round: add a small differential corpus
	for standard-library methods and iterator mutation sequences, including automatic shrinking
	and independent JavaScript result capture.

## 中文分析过程记录

<!-- 从 discovery 开始就在这里按实际顺序追加公开分析日志：detect 方向及选择原因、
可证伪假设、关键检查结果、被否定的方向和转向。完成时保留原始条目，不要重写成摘要。 -->

- 2026-09-19：已核对本轮 prompt、判定政策、Warpo 工作流及前两轮监督结果；固定基线为
	`8466a752edccaedb5de8ae3246e139a7fb71a51d`，工作树干净，Node `v24.19.0`。首选方向为普通
	表达式的引用求值次数、短路和分支语义，因为这些路径由前端直接决定，可用副作用序列和
	JavaScript 参考执行作独立 oracle。可证伪假设：至少一种受支持的复合/更新/可选表达式会
	重复求值其 receiver、错误求值未选分支，或破坏规范要求的先后顺序；最便宜检查是最小 AS
	导出函数与等价 JavaScript 的整数编码结果对比。
- 2026-09-19：表达式静态审计发现 prefix property update 和 indexed update 也会重复编译
	receiver/index，但决定行为的路径仍是上一轮 C-001 已报告的 unary update 未缓存
	`AssignmentAccessContext`，故按重复根因排除，不作为本轮候选。转向常用标准库和闭包 lowering：
	(1) `String.replaceAll` 单次倍增可能不足以容纳长 replacement，预测结果被截短；(2) 空 needle
	的 `indexOf`/`lastIndexOf` 可能在处理 `start` 前提前返回；(3) 默认 `i32` sort 比较器用减法，
	预测在正负极值间溢出并错序；(4) Map 迭代期间删除再插入触发压缩时，物理下标迭代器可能
	跳过仍存活元素；(5) captured `var` 的 for-loop 可能被错误赋予逐迭代绑定。依次用最小源码
	和普通对照值验证，优先保留无需极端错误参数的行为。
- 2026-09-19：`artifacts/C-001.ts` 在固定基线上确认 `String.replaceAll` 扩容缺陷。
	`"ab".replaceAll("a", "0123456789")` 编译成功但执行时在标准库内 abort，进程退出 `1`；
	邻近对照 `"abcde".replaceAll("a", "---").length` 返回 `7`、退出 `0`。决定代码仅将容量
	从 `thisLen` 左移一次，仍小于本次写入所需的 `replaceLen`；等价 JavaScript 应返回长度 `11`。
	该候选保留，后续还需运行独立 oracle 并记录完整命令。
- 2026-09-19：`artifacts/C-002.ts` 确认空 needle 搜索在归一化 `start` 前提前返回：基线
	`indexOf("", 2) * 10 + lastIndexOf("", 1)` 得到 `3`，非空 needle 对照得到 `11`；规范预期为
	`21`。`artifacts/C-003.ts` 也确认默认有符号整数比较器的减法溢出：`[i32.MAX_VALUE, -1]`
	排序后首项仍为 `2147483647`，而非溢出对照 `[i32.MAX_VALUE, 0]` 首项为 `0`。两者暂时保留；
	因 C-002 影响较窄、C-003 使用边界值，将继续验证 Map 迭代压缩和 captured `var`，若出现更普通、
	契约更清晰的错误则替换低价值项，而不凑数。
- 2026-09-19：`artifacts/C-004.ts` 确认 Map iterator 在结构变异触发 `rehash` 压缩后跳过
	存活条目。迭代器先产出键 `1`，删除键 `1`、`2` 后插入键 `5`，基线下一项错误为键 `4`；
	只删除键 `2`、不触发压缩的对照下一项为键 `3`。现有 `std/map-iterator.ts` 明确测试迭代期间
	新增和删除，`Map` 源码也声明 entries 按插入顺序，因此该普通变异场景有清晰产品契约。
	根因是 iterator 保存旧物理下标 `i`，而 `rehash` 把存活 entries 压到新数组前部却不调整它。
- 2026-09-19：`artifacts/C-005.ts` 的 captured `var` 与 `let` 均返回 `1`。若沿用
	TypeScript/JavaScript 语义，`var` 的两个闭包应共享函数级绑定并在循环后都读到 `2`，编码结果
	应为 `22`；静态路径也显示 closure scanner 未按声明种类区分逐迭代 tuple。不过 AssemblyScript
	可能有意统一声明作用域，因此当前只记为“行为已复现、契约待查”，不会在确认语言意图前报告。
- 2026-09-19：仓内没有找到 AssemblyScript 对 `var` 闭包作用域的明确承诺，且 Warpo closure
	文档仍标为 nightly，故 C-005 的差异缺少足够契约证据，按 admission gate 排除。C-003 排序
	溢出虽真实，但依赖跨越完整 `i32` 符号范围的边界值，价值低于已确认的普通字符串与 Map 场景，
	不纳入最终三个候选。为保持一个候选对应一个最小根因，C-002 缩减为仅验证
	`"abc".indexOf("", 2)`，不再把 `lastIndexOf` 的相邻缺陷合并计数。
- 2026-09-19：更正 C-004 初始对照说明：四键版本删除一个键后再插入也会触发扩容式
	`rehash`，只是碰巧未跳项。最终重命名为 `artifacts/C-003.ts` 的对照改为三键、删除键 `2`
	后插入键 `4`，容量未满且确定不进入 `rehash`；预期和基线下一项均为键 `3`。独立 Node
	oracle 已执行，三个入选候选分别得到 C-001 长度 `11`、C-002 索引 `2`、C-003 下一键 `3`，
	与 Warpo 的 abort、`0`、`4` 一一冲突。
- 2026-09-19：尝试把 C-001 replacement 缩到 5 字符时，基线返回正确长度 `6`，因此否定
	“刚超过逻辑倍增容量就必然可观察失败”的更强假设；分配器实际容量余量会暂时掩盖错误。
	恢复已稳定触发 abort 的 10 字符输入。根因仍由 `offset + chunk + replaceLen > outSize` 后只执行
	一次 `outSize <<= 1` 明确支持，但报告仅陈述已执行的 10 字符复现，不声称最小失败阈值。
- 2026-09-19：最终重新编译并执行三个独立源码：C-001 compile `0`、reproduce `1`、control
	`0`；C-002 compile/reproduce/control 均为 `0`，输出分别为 `0`/`1`；C-003 三者均为 `0`，
	输出分别为 `4`/`3`。三个 Node.js 独立 oracle 分别为 `11`、`2`、`3`。本轮最终报告三个
	`accept/high` 候选；未修改 `upstream/warpo`，无环境阻塞。
