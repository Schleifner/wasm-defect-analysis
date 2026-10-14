# AI Defect Analysis Report: Warpo optimization passes reachable from supported AssemblyScript; identify five distinct reproducible defects, prioritizing semantic preservation in optimization over frontend compilation

## Run Metadata

- Run ID: `round-004-warpo`
- Prompt: `defect-discovery`
- Model: `GitHub Copilot`
- Target: `warpo`
- Baseline commits: Warpo `0637147a700aacd5c8913b639f1ded3a8aebaaf7`, wasm-compiler `N/A`

## Analysis Scope

- Primary focus: `upstream/warpo/passes/` optimization semantics and interactions
	reachable from supported AssemblyScript source.
- Frontend inspection is limited to proving that candidate IR shapes are produced by
	the supported source pipeline.
- Goal: five distinct candidates passing the unchanged report admission gate.

## Candidate Findings

<!-- Include only reproduced accept, downgrade, or defer candidates. Omit hypotheses
the AI rejects. Use one independently minimized source artifact per candidate. Write
"No findings" when no candidate passes the report admission gate. -->

### C-001: Immutable-load elimination ignores reachable stores

- Location: `upstream/warpo/passes/ImmutableLoadEliminating.cpp`, `ImmutableLoadEliminating::visitLoad`
- Hypothesis: a constant-address load in a frontend-marked immutable range is folded to its data-segment initial value even when valid source performs a reachable raw store to that address first.
- Root cause: `visitLoad` checks only that the constant address lies in `immutableDataRanges_`; it does not prove that no reachable store can alias the range. For a static function object, the second load is therefore replaced with the original function index after the source increments that word.
- Impact: optimized output silently observes stale memory and returns `0` instead of the stored delta `1`.
- Reproduction: `runs/round-004-warpo/artifacts/C-001.ts`; `node upstream/warpo/dist/warpo.js runs/round-004-warpo/artifacts/C-001.ts -o runs/round-004-warpo/artifacts/C-001-O0.wasm --exportRuntime --optimizeLevel 0 --shrinkLevel 0 && node upstream/warpo/dist/warpo.js runs/round-004-warpo/artifacts/C-001.ts -o runs/round-004-warpo/artifacts/C-001-O3.wasm --exportRuntime --optimizeLevel 3 --shrinkLevel 0 && node scripts/run_warpo_wasm.mjs runs/round-004-warpo/artifacts/C-001-O0.wasm mutateFunctionIndex && node scripts/run_warpo_wasm.mjs runs/round-004-warpo/artifacts/C-001-O3.wasm mutateFunctionIndex`; exit `0`; output `mutateFunctionIndex=1` then `mutateFunctionIndex=0`.
- Independent oracle: official AssemblyScript 0.28.9, compiled with `upstream/warpo/node_modules/.bin/asc runs/round-004-warpo/artifacts/C-001.ts -o runs/round-004-warpo/artifacts/C-001-asc.wasm --exportRuntime --optimizeLevel 3 --shrinkLevel 0`, returns `mutateFunctionIndex=1`.
- Negative/control case: `C-001-control.ts` performs the same write-after-read on dynamic `ArrayBuffer` storage; Warpo O0 and O3 both return `mutateDynamicData=1`.
- AI recommendation: `accept`
- AI value: `low`
- AI value rationale: this is a clear silent miscompile of valid source, but it requires low-level `changetype`, `load`, and `store` access to function-object representation rather than an ordinary typed operation.

### C-002: GC leaf filtering drops roots across reentrant host imports

- Location: `upstream/warpo/passes/helper/BuildCallGraph.cpp`, `CallGraphBuilder::createResults`; `upstream/warpo/passes/GC/CollectLeafFunction.cpp`, `collectLeafFunctions`; `upstream/warpo/passes/GC/LeafFunctionFilter.cpp`, `LeafFunctionFilter::runOnFunction`
- Hypothesis: optimized GC lowering treats every imported call as unable to collect, so a live local object is not rooted while a host import synchronously re-enters the module and triggers collection.
- Root cause: imported functions receive empty call-graph entries and are classified as leaf. `LeafFunctionFilter` then invalidates liveness used only across that call. O0 stores `live` through `__localtostack` before `reenter`; O3 leaves it only in a Wasm local. Reentrant `churn()` collects the unrooted object and allocates `Box(99)` at the same address, so the resumed caller reads replacement data.
- Impact: valid host integration causes deterministic use-after-collection and silent data corruption (`99` instead of `7`) only in optimized output.
- Reproduction: `runs/round-004-warpo/artifacts/C-002.ts` with `C-002-run.mjs`; `node upstream/warpo/dist/warpo.js runs/round-004-warpo/artifacts/C-002.ts -o runs/round-004-warpo/artifacts/C-002-O0.wasm --exportRuntime --optimizeLevel 0 --shrinkLevel 0 && node upstream/warpo/dist/warpo.js runs/round-004-warpo/artifacts/C-002.ts -o runs/round-004-warpo/artifacts/C-002-O3.wasm --exportRuntime --optimizeLevel 3 --shrinkLevel 0 && node runs/round-004-warpo/artifacts/C-002-run.mjs runs/round-004-warpo/artifacts/C-002-O0.wasm && node runs/round-004-warpo/artifacts/C-002-run.mjs runs/round-004-warpo/artifacts/C-002-O3.wasm`; exit `0`; output `importedCollection=7` then `importedCollection=99`.
- Independent oracle: official AssemblyScript 0.28.9, compiled with `upstream/warpo/node_modules/.bin/asc runs/round-004-warpo/artifacts/C-002.ts -o runs/round-004-warpo/artifacts/C-002-asc.wasm --exportRuntime --optimizeLevel 3 --shrinkLevel 0` and run through the same host, returns `importedCollection=7`.
- Negative/control case: pass `noop` as the runner's second argument to suppress re-entry; both O0 and O3 return `importedCollection=7`, isolating the failure to collection during the imported call.
- AI recommendation: `accept`
- AI value: `high`
- AI value rationale: ordinary valid managed objects and host imports can silently corrupt live data under optimization; explicit `__collect` only makes a collection that could otherwise occur nondeterministically reproducible.

### C-003: Immutable global closure roots are removed although globals do not trace function references

- Location: `upstream/warpo/passes/GC/ImmutableGlobalToStackRemover.cpp`, `CallReplacer::visitCall`; `upstream/warpo/assemblyscript/src/builtins.ts`, `compileVisitGlobals`
- Hypothesis: optimized GC lowering removes the temporary root for an immutable global closure on the assumption that the global visitor keeps it alive, but `compileVisitGlobals` only emits visits for class references and omits function-reference globals.
- Root cause: a `const` global holding a dynamically allocated closure is marked immutable. `ImmutableGlobalToStackRemover` therefore unwraps `__tmptostack(global.get $reader)`. Function-reference types have no `getClass()` result, so `compileVisitGlobals` does not scan `reader`; collection while evaluating the next call argument reclaims both the closure object and its captured environment. A replacement closure then reuses that storage, and the pending callback observes `99` instead of `7`.
- Impact: optimized code silently calls a different closure state after ordinary argument evaluation triggers collection; any immutable global capturing runtime state can become dangling.
- Reproduction: `runs/round-004-warpo/artifacts/C-003.ts` contains two top-level assertions that `reader()` returns `7`, with `invoke(reader, (__collect(), replacement = make(99), 0))` between them; the module start function executes them during instantiation, without exports. The GC and replacement are inlined into the second argument. The noinline `invoke` helper is retained so the callback is evaluated as the first argument and remains live across evaluation of that collecting second argument. Compile with `node upstream/warpo/dist/warpo.js runs/round-004-warpo/artifacts/C-003.ts -o /tmp/C-003-assert-O0.wasm --exportRuntime --optimizeLevel 0 --shrinkLevel 0` and the corresponding O3 command using `C-003-assert-O3.wasm` / `--optimizeLevel 3`. Instantiate each with the Node WebAssembly API and provide `env.abort`; O0 instantiation passes both assertions, while O3 fails the second assertion.
- Independent oracle: the immutable binding is initialized once with `make(7)` and is never assigned again, so the source-level callback result is necessarily `7`; focused pass diagnostics confirm that only O3 removes its temporary root. Official AssemblyScript 0.28.9 cannot compile this Warpo-supported closure extension (`AS100: Not implemented: Closures`), so it is not claimed as an oracle here.
- Negative/control case: `C-003-control.ts` changes only the global binding from `const` to `let`, preventing `ImmutableGlobalToStackRemover` from deleting the temporary root; Warpo O0 and O3 both return `mutableGlobalClosure=7` under the same forced collection and replacement allocation.
- AI recommendation: `accept`
- AI value: `high`
- AI value rationale: this is deterministic silent corruption of a supported high-level closure held in a normal immutable global; no raw memory or host re-entry is required.

### C-005: Set-only closure cleanup assumes every environment operand is a load

- Location: `upstream/warpo/passes/Closure.cpp`, `SetClosureEnvRemover::visitCall`; `upstream/warpo/assemblyscript/src/compiler.ts`, `compileCallDirectWithOperands`
- Hypothesis: directly calling a function marked closure-related by a dead captured child emits `setClosureEnv(i32.const 0)`, and set-only cleanup aborts because it assumes that every operand is an `i32.load` from a function object.
- Root cause: capture analysis marks `outerWithUnusedClosure` as a closure function even though its child closure is in a statically dead branch. A direct call to that function emits `setClosureEnv(0)`. With no live environment read in the module, lowering selects `SetClosureEnvRemover`, whose first action is `dynCast<wasm::Load>()` followed by an assertion; a constant zero is valid producer output but violates that unchecked pass assumption.
- Impact: ordinary valid source containing a dead captured closure aborts the native compiler at O0 and O3 instead of producing a module whose export returns `42`.
- Reproduction: `runs/round-004-warpo/artifacts/C-005.ts`; commands `upstream/warpo/build/warpo/warpo_asc runs/round-004-warpo/artifacts/C-005.ts -o runs/round-004-warpo/artifacts/C-005-O0.wasm --exportRuntime --optimizeLevel 0 --shrinkLevel 0` and the same command with `C-005-O3.wasm` / `--optimizeLevel 3`; each exits `134`, produces no output artifact, and reports `Closure.cpp:114: Assertion 'load && "first operand of setClosureEnv must be i32.load"' failed`.
- Independent oracle: the only closure expression is unreachable under literal `false`, so the export has the unambiguous result `42`; more fundamentally, valid supported closure syntax must not trigger an internal assertion. No official asc oracle is claimed because AssemblyScript 0.28.9 does not implement Warpo closures.
- Negative/control case: `C-005-control.ts` retains the same dead arrow but changes it to return `0` instead of capturing `value`; native O0/O3 compilation exits `0`, and both outputs execute `directPlainFunction=42`.
- AI recommendation: `accept`
- AI value: `high`
- AI value rationale: a normal dead branch, including code disabled by a compile-time condition, can deterministically crash compilation solely because it contains a valid capture.

## Human Review

<!-- Review each candidate here. No additional Python checker is required. -->

### C-001

- Final decision: `reject`
- Value: `high`
- Review: 优化Pass的bug，O0和O3下的函数返回值不同。这是一个好的detect bug思路，对可疑的pass bug做无优化的对比测试，同样一个warpo的环境。但是reject，因为In Warpo, compiler-generated static function objects are immutable. Modifying their internal fields, such as _index or _env, through raw memory writes is unsupported and constitutes undefined behavior. The compiler may assume these fields never change and fold loads accordingly; behavior after such modifications is not guaranteed to be consistent across optimization levels.We are therefore closing this issue and retaining the current optimization pass. 即便如此，这类bug还是可以提出了，开发人员在debug过程中有收获
- ticket链接加入Oracle：https://github.com/wasm-ecosystem/warpo/issues/656

### C-002

- Final decision: `reject`
- Value: `none`
- Review: 在passes/helper/BuildCallGraph.cpp中有注释：we treat imported function as leaf function because in wasm-compiler, nest wasm call is not allowed. 这不是一个bug但是暴露了warpo在为了兼容后端编译器的做的一些妥协没有被明确列出来，导致部分开发者不知情。这里不支持的原因是wasm-compiler中的缺陷，这里不多解释。

### C-003

- Final decision: `accept`
- Value: `high`
- Review: 运行时bug，很好的发现。在这之前没有意识到visit不到闭包函数引用

### C-005

- Final decision: `accept`
- Value: `high`
- Review: pass的健壮性问题，没有考虑到参数可能是i32.const 0，导致编译器pass中发生crash显然是bug没有任何争议，值得修复
- ticket链接加入Oracle：https://github.com/wasm-ecosystem/warpo/issues/671

## Summary

- Reported candidates: 5. AI high-value yield: 3/5 reported candidates.
- AI recommendations: 5 `accept`, 0 `downgrade`, 0 `defer`.
- AI value ratings: 3 `high`, 2 `low`, 0 `unknown`.
- Areas searched with no findings: constructor allocation outlining; tail-call return-point
	conversion, including managed recursive frames; merge-data behavior reachable without imported
	memory; closure environment caching and forced inlining; conditional-return lowering; indirect
	call-graph propagation; GC temporary liveness, slot coloring, shrink wrapping, and early returns
	across branch, loop, property, array, constructor, and multi-argument evaluation shapes.
- Unresolved checks and environmental blockers: none for the five reported candidates. Official
	AssemblyScript 0.28.9 cannot serve as a closure oracle because it rejects Warpo's closure
	extension; C-003 through C-005 instead use source invariants, pass diagnostics, and focused
	controls. The JavaScript CLI does not propagate native assertion failures, so native
	`warpo_asc` exit status was required for C-004 and C-005.
- Suggested prompt or infrastructure change for the next round: make the JavaScript compiler
	wrapper propagate native signal failures as nonzero exits, and add a small O0/O3 differential
	harness that records compiler status, output existence, runtime result, and a paired control.

## 中文分析过程记录

<!-- 从 discovery 开始就在这里按实际顺序追加公开分析日志：detect 方向及选择原因、
可证伪假设、关键检查结果、被否定的方向和转向。完成时保留原始条目，不要重写成摘要。 -->

- 2026-09-20：建立 round 004，固定 Warpo `0637147a700aacd5c8913b639f1ded3a8aebaaf7`。本轮优先检查正常 AssemblyScript 可达的优化 pass 语义保持问题，因为优化前后执行结果可作为低成本、独立性较强的差分 oracle；前端仅用于确认 IR 形状可达。目标为 5 个通过既有 admission gate 的独立缺陷，不因数量目标降低门槛。
- 2026-09-20：首查 `ImmutableLoadEliminating`，因为它直接把前端标记范围内的常量地址 load 替换为 data segment 初值，代码未检查同模块 store。可证伪假设：静态函数对象被标记 immutable 后，受支持源码用 `store<u32>` 改写其函数索引，再用 `load<u32>` 读取；若 O3 仍返回旧值而 O0 返回新值，则该 pass 错误消除了写后读。廉价对照是对动态分配对象执行同样写后读，其地址不在 immutable range 中，应在 O0/O3 均返回新值。
- 2026-09-20：C-001 基线差分命中：同一源码 O0 执行 `mutateFunctionIndex=1`，O3 执行 `mutateFunctionIndex=0`。这证明不是仅有可疑代码，而是优化改变了写后读语义；下一步用动态分配内存做负对照，并查看 O3 WAT 是否把第二次 load 折叠为初始函数索引。
- 2026-09-20：C-001 负对照中动态 `ArrayBuffer` 的同样写后读在 O0/O3 均返回 1，差分限定到 frontend 标记的 immutable data。另查 `ImmutableLoadEliminating` 浮点构造，Binaryen `Literal::castToF32/F64` 保留整数位模式且现有单测覆盖，故否定浮点误折叠方向。`InstrSimplifier` 删除未使用 load 的 trap 是源码注释明确声明的地址永远有效策略，按既有判定政策不作为候选。
- 2026-09-20：转查新加入的 `ConstructorNewOutlining`。可证伪假设：原调用先求值 allocation operand 再求值构造参数；pass 把 allocation 复制进 helper body，却把参数作为 helper operands，导致参数先求值、对象后分配。用两个非循环 `new Box(makeArg())` call site 触发 outlining，以首次分配的地址顺序为观察值；单 call site 不触发 outlining，是邻近对照。
- 2026-09-20：否定上述 constructor 地址顺序候选。双 call site 返回 0、单 call site 返回 1，证明 pass 确实改变了 Warpo O0 的分配顺序，但官方 AssemblyScript 0.28.9 对同一源码也返回 0；堆地址先后不是可靠语言合同。进一步检查 GC lowering：helper 的 i32 参数进入 SSA/liveness，caller 临时引用跨 helper 调用仍由 temp stack 管理，未发现可观察悬空。该方向不进入 Candidate Findings。
- 2026-09-20：转向近期新增的 `TailCallOptimizer` 与 `computeReturnPoints`。选择原因是它把普通 call 标记为 `return_call`，一旦 CFG return-point 判断把仍有可达后继的 call 误认成尾位置，就会直接跳过副作用或返回错误值，且可用关闭 tail-call 的同优化配置作低成本对照。
- 2026-09-20：TailCall/CFG 的 blocks、loops、br/br_table、间接调用和 multivalue 路径已有针对性测试，未找到普通源码可达的错误 return point；try/catch 内转换虽可疑，但当前文档明确不支持 exception handling，故不报告。`CombineSwitchTargets` 也只合并 frontend 生成的 `__visit_members` 中结构完全相同且以 unreachable 结束的 continuation，未发现可达反例。
- 2026-09-20：转查 `MergeDataSection`。可证伪假设：pass 为节省编码把两个 active data segment 跨 gap 合并，并显式用零填 gap；当 AssemblyScript 使用受支持的 imported memory 时，原本未被 segment 覆盖的宿主预置字节应保持不变，O3 却会清零。用两个带小对齐间隙的 `memory.data` 段触发合并，host 在实例化前填 `0x7f`，O0 应保留 gap、O3 若归零即为语义变化；相邻段作为无 gap 对照。
- 2026-09-20：否定 imported-memory gap 候选。Warpo CLI 对 `--importMemory` 报 unknown 并忽略，`FileConfigOptions` 也未暴露该 AssemblyScript 选项；实际产物使用自有 memory，故该状态不能从本轮支持的公开输入边界到达。跨 gap 填零虽对 imported memory 可疑，但不能据此报告。
- 2026-09-20：转查 closure `OptLower`。选择原因是 O0 与 O3 分别走 Fast/Opt 两套 lowering，环境层级、捕获变量逃逸和共享环境均由自有 pass 重写；普通闭包源码可稳定产生目标 IR，并可直接比较闭包调用结果与副作用。
- 2026-09-20：closure 优化的环境缓存只缓存稳定的 parent-env 指针，现有 22 个 pass 单测覆盖 branches、dominators、loops 和多层捕获；递归/nullable 等补充形状未形成可证伪的错误路径，暂不报告。
- 2026-09-20：在 GC leaf 分析发现更强假设：`CallGraphBuilder` 为 imported function 建空边，`LeafFunctionCollector` 因而把它们视作 leaf，`LeafFunctionFilter` 会删除跨 imported call 的对象根。Warpo 文档允许 Node 等通用 Wasm runtime，合法 host import 可重入模块调用导出的 `__collect`。预测：局部对象跨该 import 后被错误回收并由下一次分配复用，O3 读到覆盖值；O0 保守 lowering 保留原值。非重入 import 是负对照。
- 2026-09-20：否定 imported-call GC 候选。把字段值改为导出参数以阻止常量传播后，O0/O3 均返回 7；O3 WAT 还明确显示 `collect` 前把 live object 写入 shadow stack。因此这个实际源码形状没有漏根，静态 call graph 疑点未转化为错误，不进入 Candidate Findings。
- 2026-09-20：继续审计近期 pass 历史。`ReturnParamFunctions` 对显式/隐式 return、带值 branch、loop 已有较完整覆盖；`CombineSwitchTargets` 的等价比较包含完整表达式树及 label，且要求 continuation 以 unreachable 结束，未形成反例。转回 `ConstructorNewOutlining` 的另一个独立不变量：pass 仅按 constructor target 分组，却把第一个 call site 的 `__new(size, id)` 复制到共享 helper。若基类和无显式构造器的派生类共用 constructor target而 allocation 元数据不同，预测 O3 会给其中一个对象错误的 size/type id，O0 与官方 AS 保持各自类型。
- 2026-09-20：否定 inherited-constructor 元数据候选。`Base` 与无显式 constructor 的 `Derived` 组合在 O0/O3 均返回正确位掩码 6；frontend 没有产生“同 constructor target、不同 `__new` 元数据”的形状。后续改用 GC 子 pass 独立开关做 O3 控制组差分，以便把错配定位到具体优化。
- 2026-09-20：复核 imported-call GC 探针时发现先前否证不充分：caller 在 import 返回后执行的 `new Box(99)` 本身是已知可 GC 调用，迫使 O3 为 `live` 保留根，掩盖了 import 被判 leaf 的影响。修正实验让 host callback 同步重入导出的 `churn()`，在重入调用内先 `__collect` 再分配 replacement；caller 返回后只读字段。这样 `live` 仅跨 imported call，预测 O0 返回 7、启用 leaf filter 的 O3 返回 99。
- 2026-09-20：修正后的 C-002 命中：同一源码和 host 下 Warpo O0 返回 7、O3 返回 99；no-op import 对照在 O0/O3 均返回 7，官方 AssemblyScript 0.28.9 在实际重入下返回 7。WAT 结构也吻合：O0 在 import 前以 `__localtostack` 保根并维护 shadow frame，O3 直接跨 `reenter` 保存在 Wasm local。此前经 JS CLI 传入 `--no-gc-opt` 被明确报 unknown 并忽略，故不把该次结果当 pass 隔离证据。
- 2026-09-20：继续审计 closure `OptLower` 的缓存失效模型。缓存来源是当前函数固定的 heap-env local，普通子调用不会改写该 local；现有 pass 单测已覆盖分支、支配关系、循环外提和多层 parent-env，未找到“兄弟闭包切换导致同一函数缓存失效”的可达状态，故停止该方向。随后检查 `call_ref`，但 Warpo 状态文档将 Reference Types 与 Typed Function References 列为未实现，普通函数值仍生成 `call_indirect`，该 IR 缺口不满足源码可达性。
- 2026-09-20：转向 GC 临时对象 liveness，因为 `ObjLivenessAnalyzer::TmpUses` 需要穿过 block/loop/if 等包装找到 `__tmptostack` 的真实使用点，错误边界会让对象在后续可收集调用前失根。可证伪探针让条件表达式产生临时 `Box`，第二个实参执行 `__collect()` 并分配 `Box(99)`；若分支结果未活跃到外层调用，O3 将返回 99，而 O0、官方 asc 与无条件包装控制应返回输入值。
- 2026-09-20：条件临时假设被执行否证：选择 true 分支时 O0/O3 均返回 7，false 分支均返回 8；`TmpUses` 对该 block/if 结果的使用传播正确。转查 `MergeSSA` 的链式对象别名合并：若方法返回新对象却被错误归并到 receiver 的根，下一次链式调用内 collection 可能回收仍需使用的返回对象。
- 2026-09-20：`MergeSSA` 只沿所有返回点都返回未修改同一参数的函数合并，源码层“返回新对象却被当 receiver”的假设不成立。补跑 GC 边界矩阵：两个同时存活对象在 O0/O3 分别一致返回 16/15；条件分配路径一致返回 1/7；noinline identity 链一致返回 7。因此 slot 冲突着色、条件 shrink-wrap 和 return-param alias 在这些可达形状上均未暴露错误，继续转向其他 O3 pass。
- 2026-09-20：检查 `ImmutableLoadEliminating` 的跨范围 load，确认 `contains(offset, size)` 要求完整 load 区间落在同一个 immutable range，且单测覆盖尾端不足及相邻范围，故否定该方向。转查 `ConditionalReturn` 后形成可执行假设：它匹配 void 函数中的任意 `return`，但替换为 `br_if` 时只保留 condition；合法源码 `if (condition) return sideEffectingVoidCall()` 的 return value 虽为 void 仍须求值，O3 可能丢失调用副作用，O0 与官方 asc 应保留。
- 2026-09-20：`ConditionalReturn` 探针被否证：`return mark()` 在 frontend IR 中已保持为先调用 `mark` 再执行无值 return，O0/O3 对 true/false 均返回 42/1。另检查 `call_indirect`：建图会枚举 table 内所有签名匹配目标，leaf filter 对间接调用更是无条件保留跨调用根，故不能复现 imported-call 的漏根机制。
- 2026-09-20：执行 10 类 GC 生命周期矩阵，覆盖多实参求值、临时 receiver、数组元素、构造器实参、分支合流 local、覆盖后别名、闭包捕获、间接调用和循环携带对象；O0/O3 的结果逐项一致（15、7、15、15、8/7、77/78、7、7、7/8）。这些普通 source-level 形状未发现新的 GC 缺陷。
- 2026-09-20：回到 closure `OptLower`，改用可达 raw-memory 状态转换而非闭包调用切换。returned inner function 的 `+4` 字段是 middle env，middle env 首字是 outer env；探针先读 level-2 捕获值，再 `store` 将 parent link 改为另一实例的 outer env，然后再次读取。预测 FastLower 每次重走链返回 79，OptLower 若未把任意 memory write 视为 cache invalidation 则复用旧 level-2 env 并返回 77。
- 2026-09-20：closure parent-link 变更假设被否证：O0/O3 均返回 79。O3 WAT 显示第一次 outer 捕获值被单独缓存，但源码 raw store 后的第二次读取仍从 middle env 重新加载 parent link，没有跨该转换复用旧 outer env；因此不报告此方向。
- 2026-09-20：转查 `InlinedDecoratorLower` 与 closure lowering 的次序。该 pass 在 closure 伪指令降低之前复制 `@inline` callee body，而 `getClosureEnvByLevel(level)` 的 level 是按原 callee 词法层级编码，后续 lowering 却按当前 caller 查询 heap-env local。可证伪假设：父函数内的 `@inline` 嵌套函数捕获父 local；若复制后层级未重写，O0/O3 会从错误 parent env 读取而非返回 42。最小反证是两种优化级别与官方 asc 都返回 42。
- 2026-09-20：`inline.always` 调用点版本在 Warpo O0/O3 均返回 42，closure 层级在该可达形状中保持正确；官方 asc 0.28.9 不实现 closure，报 `AS100: Not implemented: Closures`，故不能充当此方向的独立 oracle，探针不提升为候选。
- 2026-09-20：转查 `MergeSSA` 对“返回原参数”的方法链合并。可证伪假设：方法 receiver 先求值形成临时根，后续参数表达式把保存 receiver 的 local 改指向新对象，再触发 collection；若 pass 把 receiver 临时 SSA 错误合并到旧 local SSA 并删除独立根，旧对象会被回收并由 `Box(99)` 复用。预测 O0/官方 asc 返回 42，O3 返回 99；不改写 local 的相邻对照应均返回 42。
- 2026-09-20：receiver 重写探针在 Warpo O0、O3 和官方 asc 均返回 42；实际 liveness 保留了旧 receiver，未错误依附到 local 的新定义，故否定该 `MergeSSA` 候选。
- 2026-09-20：转查 `ShrinkWrap` 与 `ExprInserter` 的 conditional-break 边界。`insertAtEndOfBB` 对无条件 `br` 会把 epilogue 插在跳转前，却把 `br_if` 走通用 insert-after；taken edge 因而可能绕过 `__increase_sp`。可证伪探针先早退，使 managed-object 区域可被下沉；对象最后一次活跃后再按条件返回，使分流 `br_if` 成为候选 epilogue。若命中，一次 taken 调用后导出 `__stack_pointer` 比调用前少一个 frame，fallthrough 对照保持相等。
- 2026-09-20：首个 shrink-wrap 分支探针被否证。O3 WAT 在条件分流前恢复 frame；实际 taken 调用 `__stack_pointer` 为 `34360→34360`，fallthrough 也相等，O0 为 `33336→33336`。代码中的 conditional-break insert-after 缺口尚未证明可由当前源码 CFG 选作 epilogue，故不报告。
- 2026-09-20：转查 `ImmutableGlobalToStackRemover`。该 pass 删除 immutable `global.get` 外的 `__tmptostack`，依赖 global 一直由 GC visitor 保活；但 `compileVisitGlobals` 只枚举 `globalType.getClass()`，函数/closure reference 可能被跳过。可证伪探针让全局 `const` 保存 `make(7)` 创建的动态捕获 closure，调用时先读取它，再在第二参数求值中 collection 并创建同形 `make(99)`。若 O3 删除了唯一临时根且 visitor 未扫描 global，O0 返回 7，O3 将读到 99 或失效对象；mutable global 作为相邻控制。
- 2026-09-20：C-003 命中并通过控制：最终 artifact 的 O0/O3 分别返回 7/99；仅把 global 从 `const` 改为 `let` 后两者均返回 7。focused debug 明确显示 `GCImmutableGlobalToStackRemover` 在 `immutableGlobalClosure` 删除 `global.get reader` 外的 `__tmptostack`，而生成的 `__visit_globals` 只访问临时 `closure/env`、不访问 `reader`，与动态 closure 存储被 99 复用的结果一致。
- 2026-09-20：继续检查与 C-002 不同的内部间接调用传播。可证伪假设：`invoke(callback)` 内的 `call_indirect` 若未被 `BuildCallGraph` 关联到会 collection 的 table target，`invoke` 会被误判 leaf，外层 direct caller 将删除跨 `invoke` 的 `live` 根。探针让 target collection 后分配 `Box(99)`；预测正确建图时 O0/O3 均返回 7，漏边时 O3 返回 99。
- 2026-09-20：普通 frontend table 的 indirect wrapper 假设被否证：Warpo O0、O3 与官方 asc 均返回 7。默认 element segment 名称与 table 名称一致，`BuildCallGraph` 能按签名枚举到 collection target，并将非 leaf 性质传播给 outer caller；不报告此方向。
- 2026-09-20：从 shrink-wrap 历史修复转向 `PrologueOnly` 状态。该状态把 prologue 下沉到首个 managed 区域，却调用 `replaceReturnExprWithEpilogue` 遍历并改写函数内所有 return。可证伪假设：位于下沉 prologue 之前的 guard return 会执行没有配对 decrease 的 `__increase_sp`。探针让 early=false 路径创建并跨 collection 使用对象，使 prologue 下沉、epilogue 留在 exit；直接比较导出 `__stack_pointer` 调用前后，预测 O3 early=true 增加 4，O0 及 O3 early=false 保持不变。
- 2026-09-20：`PrologueOnly` 早退假设在首个可达形状中被否证：O0/O3 early=true 与 O3 normal path 的 stack pointer 均调用前后相等。focused diagnostic 显示该函数选择 `prologue = i32.const 4, epilogue = return` 并成功进入 `opt/opt`，两个 frame 操作都留在 managed 分支内，guard return 未被错误增加。
- 2026-09-20：转查 `InlinedDecoratorLower` 与 closure 元数据更新。强制 inline 在 closure lowering 之前复制 callee body和 locals，但 `VariableInfo` 的 heap-env local 索引按原函数建立。可证伪假设：把创建捕获 closure 的 `make(7)` 用 `inline.always` 复制到原本不创建 closure 的导出函数，会让后续 closure lowering 查询/使用错误 heap local，表现为编译断言、验证失败或 callback 不返回 7；不 inline 的同一 factory 是控制。
- 2026-09-20：forced-inline closure factory 在 Warpo O0/O3 均返回 7，未出现 metadata/local 索引错绑，否定该形状。随后扩大 GC 差分矩阵到此前未覆盖的 switch、短路条件、ternary 后续多参数、getter/setter、复合属性赋值、数组 store、嵌套构造、链式赋值、二元对象结果、不对称分支和 disjoint slot；这些形状同时压力测试 liveness use-site、求值顺序和 slot coloring。
- 2026-09-20：扩展矩阵的 20 个执行点在 Warpo O0/O3/官方 asc 全部一致：switch 为 7/87/8，短路为 8/7/7/7，ternary 多参数为 234/134，其余 getter、setter、复合赋值、array store、构造、别名和 slot 用例也均符合预期。未发现新增 GC optimizer 差分。
- 2026-09-20：转查 closure set-only lowering。`SetClosureEnvRemover` 在模块有 `setClosureEnv` 但无 closure-env global 时删除调用，却断言 operand 必须为 `i32.load`；前端直接调用 nested closure function 时可生成 `setClosureEnv(i32.const 0)`。可证伪探针为不捕获变量的局部函数被直接调用；若 frontend 仍标记其 closure ABI，Warpo 在 O0/O3 lowering 应触发断言，而普通顶层函数控制正常。
- 2026-09-20：不捕获变量的 direct nested function 在 O0/O3 均编译并返回 42，frontend 未产生触发 set-only assertion 的目标形状，故否定该探针。接着检查动态 closure callee 临时值：`make(7)(collectAndReplace())` 必须在参数 collection 期间保活 callee；若 frontend 的 raw i32 temp 与 O3 GC root pruning 组合漏根，O3 将返回 100，O0 应返回 8。并用最小 tail recursion 验证 `--enable-feature tail-call` 产物能否在当前 Node 执行，再决定是否深入该 pass。
- 2026-09-20：callee 临时值探针在 O0/O3 都返回 100（源码期望 8），确认 frontend 将动态 closure callee 保存在非 managed i32 local 的独立真实缺陷；但它不依赖优化，按本轮 pass 优先范围不提升为候选。基础 tail recursion 在 feature-on 的 O0/O3 都返回 1000，确认当前 Node 可执行 tail-call 产物，但尚未压力测试 GC frame 与 epilogue。
- 2026-09-20：三路聚焦审计未得到新的合格候选：tail/inlining 的可达 CFG 有直接测试，remaining-pass 的可疑状态要么 producer 不生成、要么缺少源码合同；GC 审计提出 multi-return tuple sibling，但 tuple 本身受 GC visitor 管理且 operands 入栈，静态证据不足。重新核对 `Runner.cpp` 发现 tail-call 在所有 GC lowering 和默认优化之后、feature 开启时确实调度；下一探针让尾递归函数持有 managed frame，直接检查 epilogue 是否可能被 `return_call` 绕过。
- 2026-09-20：managed tail recursion 在 O0/O3 feature-on 均返回 1000；O3 WAT 中每层递归 call 后仍有 `__stack_pointer += 8`，因此有 GC epilogue 的 call 不被改为 `return_call`，frame 保持配对。`ReturnPoints` 对 conditional break/fallthrough 也有精确单测，关闭该方向。
- 2026-09-20：转查文档化 FFI closure lowering。文档要求 callback 第一条调用 `ffi.set_ffi_closure_env(userData)`；可证伪假设是不捕获外层状态的 callback 产生 `hasFFISet=true`、但不产生 closure env global，common lowering 随后引用不存在的 global 或无法取得 heap local，导致合法源码编译失败。捕获变量的官方 `closure-ffi.ts` 是相邻控制。
- 2026-09-20：C-004 命中：不捕获变量的 FFI callback 在 O0/O3 都于 `Closure.cpp:143` 断言缺少 `heapVariableStorageLocalIndex`；直接运行 native `warpo_asc` 的真实退出码为 134 且不生成 wasm（JS wrapper 会错误返回 0，故不以其状态作证据）。仅增加一个真实 capture 后，O0/O3 均编译并返回 callback index 1。根因是 FFI lower 无条件要求 heap env local，而 frontend 只为 closure function 记录该 local。
- 2026-09-20：重测 set-only remover 时修正了早先不充分的 producer 形状：不捕获的 nested function不会标记外层；把捕获 `value` 的 child closure 放在 literal-false 分支，则 capture metadata 仍使外层采用 closure calling convention，但模块没有 live env read。direct call 生成 `setClosureEnv(i32.const 0)`，O0/O3 均在 `Closure.cpp:114` 因 operand 不是 load 而退出 134。
- 2026-09-20：C-005 邻近控制保留同一 literal-false arrow，仅去掉对 `value` 的 capture；O0/O3 均编译并返回 42。故失败不是 dead code 或 nested function 本身，而是 frontend 合法生成的 constant env write 与 `SetClosureEnvRemover` 的 load-only 假设冲突。至此得到 5 个机制独立且有基线复现与控制的候选。
- 2026-10-12：按复现可读性要求简化 C-003 artifact：移除 export，改为两次顶层断言 `reader() == 7`；把 GC 和 replacement 内联为第二个调用参数 `(__collect(), replacement = make(99), 0)`。尝试同时删除 `invoke` 后，O0 也失败，表明直接调用全局 callee 会引入不同生命周期形状；因此保留最小的 noinline `invoke` 以保证参数求值期间 closure 被暂存。最终 O0 两次断言通过，O3 第二次断言失败。
