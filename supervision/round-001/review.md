# Verified Bug Report

Baseline is latest warpo main branch. Each current result was checked with the same reproducer after the repair.

# Summary

- Eight findings in total.
- Findings 1 and 5 are two high-value real bugs.
- Finding 2 is a robustness issue; an assertion was added.
- Finding 3 is intended behavior, not a bug, but exposes missing comments or design documentation.
- Findings 4, 6, 7, and 8 cannot be emitted by AssemblyScript. They require hand-written WAT and do not require a Warpo fix.

## 1. Uninitialized array-destructuring `const` crashes the parser

- It should follow TypeScript semantics and must not crash. The analysis is correct.

**Old reproduction and failure.** `const [first, second]: [i32, i32];` in `const-tuple-unpack-missing-initializer.ts` reached `assert(name).range`, because an array binding has no simple identifier name. The compiler aborted instead of producing a user diagnostic.

**Root cause and repair.** `parseVariableDeclaration` assumed every uninitialized `const` had `name`. It now selects the destructuring diagnostic and takes the first binding range when the declaration has an array pattern.

**Post-fix proof.** `build/tests/frontend/warpo_frontend_test const-tuple-unpack-missing-initializer` accepts the expected `ERROR TS1182: A destructuring declaration must have an initializer.` diagnostic.

## 2. MergeDataSection requires non-overlapping AS data segments

- This is a robustness issue and the analysis is correct. An assertion is sufficient because normal AssemblyScript does not produce this case.

**Old reproduction and failure.** The pass-level input with `(data (i32.const 3) "XY")` followed by `(data (i32.const 0) "AB_CD")` contains overlapping segments, but normal AssemblyScript static-segment allocation advances `memoryOffset` by each buffer's actual size and does not produce this shape. Treating arbitrary overlapping WAT as a supported frontend input made the pass's merge semantics disagree with the AS producer's invariant.

**Root cause and repair.** `MergeDataSection` is an optimization pass for modules emitted by the AS frontend, whose active data segments do not overlap. The pass restores its address-sorted scan for that input contract and asserts after sorting that every segment satisfies `previous.end <= next.offset`. The overlap-only regression cases were removed; the remaining tests use adjacent, gapped, and unordered-but-non-overlapping segments.

**Post-fix proof.** `MergeDataSectionPassTest.*` passes all four tests, including `UnorderedOffsetsStillMergeBySortedScan`, with the non-overlap invariant enforced.

## 3. Closure lowering removes a potentially trapping argument

- This is intended behavior and not a bug. It exposes missing comments or design documentation.

**Old reproduction and failure.** Lowering `setClosureEnv(i32.load(i32.const 65536))` in a one-page memory replaced the whole call with `nop`. The out-of-bounds load therefore stopped trapping, changing observable WebAssembly behavior.

**Root cause and repair.** `SetClosureEnvRemover::visitCall` discarded an eliminated call without retaining evaluation of its argument. It now replaces the call with `drop(argument)`, which preserves loads, side effects, and traps while discarding the unused value.

**Post-fix proof.** `ClosureLower.SetOnlyPreservesPotentiallyTrappingArgument` asserts that the transformed caller body is a `drop` containing the original `load`; it passes in the focused pass suite.

## 4. ConditionalReturn can generate a colliding nested block label

- This is not a bug. Ignoring hand-written WAT that constructs the same label, Warpo does not generate this case.

**Old reproduction and failure.** A function containing a nested block named `$CONDITION_RETURN#0` received another generated block with the same name. The old root-only visitor missed nested blocks and chose `#0` again.

**Root cause and repair.** `getValidBlockName` called `visitor.visit(func->body)`, which did not recursively traverse the body. It now calls `visitor.walk(func->body)` and sees every nested block label.

**Post-fix proof.** `ConditionalReturnTest.GeneratedNameAvoidsNestedBlockName` verifies that the generated outer name is `CONDITION_RETURN#1`; it passes in the focused pass suite.

## 5. object-literal accessor initialization order

- This is a bug and the analysis is correct.

### Object-literal accessor receives the preceding field value

**Old reproduction and failure.** `({ field: 7, value: 9 } as Record).value` returned `7`: the deferred accessor setter indexed the full property-value array with its deferred-accessor index, so it reused the first field expression.

**Root cause and repair.** Accessors were deferred but their expressions were neither associated with the accessor nor retained at their source position. The compiler now evaluates each deferred accessor value into a typed temporary local during the source-order traversal. A `DeferredObjectLiteralSetter` record keeps that local coupled to its setter instance, and the setter call is still constructed later after field initialization.

**Post-fix proof.** The generated `object-literal-accessor-initializer` snapshots are current. Direct local Node/WebAssembly execution reports `accessorInitializer=9`, `accessorEvaluationOrder=11`, and `multipleAccessorInitializers=23`.

### Object-literal accessor expressions execute too late

**Old reproduction and failure.** For `{ value: ++count, field: count } as Record`, the old compiler delayed `++count` until after `field: count`. The resulting `field * 10 + value` was `1`; JavaScript/AssemblyScript source order requires `11`.

**Root cause and repair.** Deferred setters also deferred evaluation of their right-hand side. Storing the right-hand side in a temporary as the property list is traversed retains source evaluation order, while setters still run after field initialization.

**Post-fix proof.** Direct Node/WebAssembly execution of the same fixture reports `accessorEvaluationOrder=11`. The frontend fixture is snapshot-checked; its runtime phase is skipped by the existing WarpRunner because that configuration uses tail calls, so the direct execution is the runtime evidence.

## 6. Global array bindings emit the same unsupported-feature error twice

- The error is logged in multiple places. This is not a bug, robustness is unaffected, and it can be ignored.

**Old reproduction and failure.** `let [first, second] = [1, 2];` at global scope emitted `ERROR AS100: Not implemented: array binding pattern in global scope` twice.

**Root cause and repair.** `Program` already reported the unsupported global pattern, then top-level compilation reported it again for the nameless declaration. The compiler now skips that declaration after the owning program-level diagnostic has been emitted.

**Post-fix proof.** `build/tests/frontend/warpo_frontend_test global-array-unpack-errors` expects exactly one AS100 error. Direct compiler validation also observed `count=1` with the expected nonzero compiler exit.

## 7. ConstructorNewOutlining

- This case does not exist in AssemblyScript; the class id and size are fixed for a constructor of a given type.

### ConstructorNewOutlining conflates distinct allocation operands

**Old reproduction and failure.** Two calls to the same constructor using `__new(16, 4)` and `__new(32, 9)` were put in one outline group. The generated helper copied the first allocation operand, so the second call would allocate with the wrong size and runtime type identifier.

**Root cause and repair.** Candidates were grouped only by constructor name. They are now partitioned by structural equality of the allocation operand before an outline helper is created.

**Post-fix proof.** `ConstructorNewOutliningTest.DoesNotOutlineDifferentAllocations` verifies that no shared `A#constructor@new` helper is produced for those distinct operands; it passes in the focused pass suite.

### ConstructorNewOutlining copies caller-local expressions into a zero-argument helper

**Old reproduction and failure.** Repeated `__new(local.get 0, i32.const 4)` allocation expressions were copied into an outlined helper with no parameters. The helper then referenced a caller-local index that it did not own, yielding invalid WebAssembly IR.

**Root cause and repair.** Candidate collection accepted allocation expressions containing `local.get` or `local.set`. A `LocalReferenceScanner` now rejects those candidates, because the helper has no mechanism to carry caller-local values.

**Post-fix proof.** `ConstructorNewOutliningTest.DoesNotOutlineAllocationsUsingCallerLocals` verifies that no helper is emitted and validates the transformed module with `wasm::WasmValidator`; it passes in the focused pass suite.

## 8. Immutable-load folding uses the wrong byte for overlapping data segments

- This is not a bug. Warpo does not generate overlapping data-segment initialization.

**Old reproduction and failure.** Two source-order segments initialized address zero first with byte `1` and then with byte `9`. The immutable-load folder traversed forward and folded `i32.load8_u` to `1`, even though final memory contains `9`.

**Root cause and repair.** `getValueFromDataSegment` stopped at the first matching active segment. It now traverses the data-segment list in reverse declaration order, implementing last initialization wins.

**Post-fix proof.** `ImmutableLoadEliminatingTest.OverlappingDataSegmentsUseLastInitialization` verifies the folded constant is `9`; it passes in the focused pass suite.

## Aggregate verification

The focused command below passed all 41 tests across the five affected pass suites:

```sh
build/passes/warpo_passes_test \
  --gtest_filter='ClosureLower.*:ConditionalReturnTest.*:ConstructorNewOutliningTest.*:ImmutableLoadEliminatingTest.*:MergeDataSectionPassTest.*' \
  --gtest_color=no
```

The repository-level verification also passed:

- `clang-tidy -p build` on the five changed pass files completed without user-code findings.
- `npm run build` completed successfully.
- `npm run test:update` completed successfully: 66 frontend snapshots passed (260 skipped), 27 optimization snapshots ran, 16 driver tests passed, and 19 DWARF tests passed.
- `npx prettier --check` passed for the changed TypeScript, JSON, and report files.
