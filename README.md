# WASM Defect Analysis

This repository evaluates and improves AI-assisted compiler defect discovery across two projects:

- [Warpo](https://github.com/wasm-ecosystem/warpo): an AssemblyScript-to-WebAssembly frontend and optimization pipeline.
- [wasm-compiler](https://github.com/wasm-ecosystem/wasm-compiler): a WebAssembly compiler and runtime.

The workflow is evidence-first: each run pins target commits, the prompt, and experiment settings; AI produces candidates and reproduction evidence; and a human makes the final judgment. The goal is to improve precision on high-value defects rather than maximize unverified findings.

Documentation:

- [Current workflow](docs/CN-workflow.md)
- [Methodology](docs/methodology.md)
- [Supervision data and splits](supervision/README.md)
