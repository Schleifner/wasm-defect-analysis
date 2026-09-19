#!/usr/bin/env node

import { readFile } from "node:fs/promises";

function usage() {
  console.error("Usage: node scripts/run_warpo_wasm.mjs <module.wasm> <export> [args...]");
  console.error("Append n to an integer argument when the Wasm parameter is i64, for example 42n.");
}

function parseArgument(argument) {
  if (argument.endsWith("n")) {
    return BigInt(argument.slice(0, -1));
  }
  if (argument.toLowerCase() === "nan") {
    return Number.NaN;
  }
  const value = Number(argument);
  if (Number.isNaN(value)) {
    throw new TypeError(`invalid numeric argument: ${argument}`);
  }
  return value;
}

function formatValue(value) {
  if (Array.isArray(value)) {
    return `[${value.map(formatValue).join(",")}]`;
  }
  if (typeof value === "bigint") {
    return `${value}n`;
  }
  if (Object.is(value, -0)) {
    return "-0";
  }
  return String(value);
}

const [wasmPath, exportName, ...rawArguments] = process.argv.slice(2);
if (wasmPath === undefined || exportName === undefined) {
  usage();
  process.exitCode = 2;
} else {
  try {
    const wasmBytes = await readFile(wasmPath);
    const module = await WebAssembly.compile(wasmBytes);
    const unsupportedImports = WebAssembly.Module.imports(module).filter(
      ({ module: moduleName, name, kind }) =>
        moduleName !== "env" || name !== "abort" || kind !== "function",
    );
    if (unsupportedImports.length > 0) {
      const names = unsupportedImports
        .map(({ module: moduleName, name, kind }) => `${moduleName}.${name} (${kind})`)
        .join(", ");
      throw new Error(`unsupported Wasm imports: ${names}`);
    }

    let wasmExports;
    const imports = {
      env: {
        abort(message, fileName, line, column) {
          throw new Error(
            `AssemblyScript abort at ${line}:${column} (message=${message}, file=${fileName})`,
          );
        },
      },
    };
    const instance = await WebAssembly.instantiate(module, imports);
    wasmExports = instance.exports;

    const exportedFunction = wasmExports[exportName];
    if (typeof exportedFunction !== "function") {
      const available = WebAssembly.Module.exports(module)
        .filter(({ kind }) => kind === "function")
        .map(({ name }) => name)
        .join(", ");
      throw new Error(
        `Wasm function export not found: ${exportName}; available functions: ${available || "none"}`,
      );
    }

    const result = exportedFunction(...rawArguments.map(parseArgument));
    console.log(`${exportName}=${formatValue(result)}`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}