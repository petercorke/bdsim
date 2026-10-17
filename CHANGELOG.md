# Changelog

## [1.4.0](https://github.com/petercorke/bdsim/compare/v1.3.0...v1.4.0) (2026-08-19)

**Highlight** Wiki and Sphinx online documentation completely uptodate. Added proper deprecation for recent change to watch variables in `out` structure. Working against RVC3 examples at [https://github.com/petercorke/RVC3-python](https://github.com/petercorke/RVC3-python).

### Features

* add BDSIM_NO_GRAPHICS envariable to force-disable graphics ([f157f63](https://github.com/petercorke/bdsim/commit/f157f63bc1516f94cc3589e41b967a4df24952eb))
* add python -m bdsim and bdsim console script ([6ebeb22](https://github.com/petercorke/bdsim/commit/6ebeb2283aca18cd2a7b23b36154d294e77aed1b))


### Bug Fixes

* **blocks:** Dict block exposes N inputs and returns list ([208e4c6](https://github.com/petercorke/bdsim/commit/208e4c6c9611afe17a613d02f73dd4567e080eb7))
* **ci:** guard release-please's PyPI-publish trigger against the truthy-string bug ([#66](https://github.com/petercorke/bdsim/issues/66)) ([0ca95f7](https://github.com/petercorke/bdsim/commit/0ca95f7f1c87960122dd62e1eb605e51296513c6))
* deprecate out.y0/y1/... cleanly instead of breaking silently ([21ef612](https://github.com/petercorke/bdsim/commit/21ef6125862db68ef121b6e59be52f81e7983d64))
* explicitly import Counter to satisfy F405 lint ([aa6164a](https://github.com/petercorke/bdsim/commit/aa6164acba00b5943d8da12ddd1b9b2baad733c1))
* five hybrid-sim per-interval sample-grid bugs ([#36](https://github.com/petercorke/bdsim/issues/36)) ([cf46985](https://github.com/petercorke/bdsim/commit/cf469852ee0a60c875db8e82b7168d82b648730b))
* named-port assignment (block.portname = value) wired the wrong plug ([4d66715](https://github.com/petercorke/bdsim/commit/4d667156d8573728fb83e7a5fa342299baff7e16))
* PoseIntegrator_S/DPoseIntegrator crash with default x0 ([2d46cf2](https://github.com/petercorke/bdsim/commit/2d46cf2ab7ea0e56af2c3fba5c9de5ea83eeaa34))
* release-please's Trigger PyPI publish step can't detect repo ([4076e57](https://github.com/petercorke/bdsim/commit/4076e57bc5752c699ecbd77b5a4479e3acbee5ac))
* replace itertools.count() with a deepcopy-safe Counter ([6e84b46](https://github.com/petercorke/bdsim/commit/6e84b46275af0be0d7348046c40ceaf21f198786))
* restore discovery of bdsim.blocks.spatial blocks ([8fb5e08](https://github.com/petercorke/bdsim/commit/8fb5e08759f2c3316059a04ad505d88ab5a01cf2))
* Scope's watch=True silently no-ops when graphics is disabled ([7a9ad8e](https://github.com/petercorke/bdsim/commit/7a9ad8ea7a79a3ede49771c1e2d315d6dd11d120))
* Scope(watch=True) crashed on start due to attribute typo ([92cc7e0](https://github.com/petercorke/bdsim/commit/92cc7e08bc4e93d215b542364c461a6f1af92858))


### Documentation

* add AGENTS.md stub ([b06e8f7](https://github.com/petercorke/bdsim/commit/b06e8f76a906a8d5cba33101c210be2fd6411dea))
* expand AGENTS.md with block discovery and CLI entry point notes ([2c9e9cd](https://github.com/petercorke/bdsim/commit/2c9e9cd0878d99d133336c67ff98fccc61744e2d))
* match Sphinx page footer to rvc-ecosystem convention ([4fee176](https://github.com/petercorke/bdsim/commit/4fee176522de6f2ebb65f92793dad73fea32d753))
* match Sphinx page footer to rvc-ecosystem convention ([32e4d65](https://github.com/petercorke/bdsim/commit/32e4d65cd2b6f05e2321866a9617c0dd27bd491a))
* sync Sphinx docs with wiki, fix cross-references and drift ([0bc05ba](https://github.com/petercorke/bdsim/commit/0bc05ba2ef89ca44bbf33bd11b2cb0909fec6ca2))

## [1.3.0](https://github.com/petercorke/bdsim/compare/v1.2.2...v1.3.0) (2026-08-12)

**Highlight: several bugs dormant since May are fixed, the published wheel
drops from 15.5MB to ~600KB, and bdsim gets a real OIDC-based PyPI release
pipeline.**

### Bug Fixes

* restored `PROD`'s `matrix` argument, silently removed in 1.2.2 -- now emits a `DeprecationWarning` instead of erroring ([5762c87](https://github.com/petercorke/bdsim/commit/5762c87e3c81e1ce28116feff53ddd91b9c4f91c))
* fixed a missing `graphics_block.py` commit, introduced by 1.2.2's graphics-split refactor, that broke `import bdsim` from a fresh checkout (never reached a real `pip install` -- 1.2.2 itself shipped before the breaking commit landed) ([fbad240](https://github.com/petercorke/bdsim/commit/fbad240fb702da5e05ed4c210b06078dcca85a77))
* fixed broken logo/badge URLs across the README, docs front page, and notebooks, left dangling by the May `src/`-layout refactor ([5f12eeb](https://github.com/petercorke/bdsim/commit/5f12eeb991a92e027a3626b781531feaefcf6884))
* fixed a Python 3.10 `SyntaxError` in the JupyterLite build tooling, present since that same refactor ([4ae71b7](https://github.com/petercorke/bdsim/commit/4ae71b7831b7c9dab77c18f8774bec916740dbf6))
* fixed a `SyntaxWarning`-triggering docstring in `BlockDiagram.graph()`, present since 1.2.2 added the method ([ee1fdc8](https://github.com/petercorke/bdsim/commit/ee1fdc822a535839b4119e83901d1d0ca9ca9b14))
* fixed notebook images breaking specifically inside the deployed JupyterLite site ([867f90b](https://github.com/petercorke/bdsim/commit/867f90b01e1e5e412e921cfb00da9ce94327540e))
* fixed a kernel crash specific to Safari (no WebAssembly JSPI support yet) by pinning `jupyterlite-pyodide-kernel` ([4831f33](https://github.com/petercorke/bdsim/commit/4831f3321666f4588c988c50b9d6024be49648bc), [6bd280b](https://github.com/petercorke/bdsim/commit/6bd280bd8dda45bf4b713f8b29f3730f7c290f21))
* the published wheel dropped from 15.5MB to ~600KB -- `bdedit`'s stale, long-orphaned Sphinx build output and unused reference images are no longer bundled into every install ([8575203](https://github.com/petercorke/bdsim/commit/8575203b2893b15b071bada31ecc76dd6e554840), [e6be68d](https://github.com/petercorke/bdsim/commit/e6be68da4d40bd545fb55ba7097fa9a685bd415b))
* `numpy>=2` is now the accurate, CI-tested floor (previously `numpy>=1.17.4`, untested for years) ([c6ae9fc](https://github.com/petercorke/bdsim/commit/c6ae9fc5178a3b4101ecb42e40b5c8ae8df4d87b))

### Build System

* added a real OIDC-based PyPI release pipeline ([7d6aa7f](https://github.com/petercorke/bdsim/commit/7d6aa7f0398df83248e8e1809a0d40df13ed7a4a)) and Conventional-Commit PR title enforcement ([8206722](https://github.com/petercorke/bdsim/commit/8206722b223a3ba321c093fa44095f298cdc38d3)), replacing the previous by-hand `make upload`


## [1.2.2](https://github.com/petercorke/bdsim/compare/v1.2.1...v1.2.2) (2026-05-26)

**Highlight: diagram export and graphics.** `BlockDiagram.graph()` brings
DOT/Mermaid/GraphML/ELK export, a generic `ANIMATION` block, per-block
movie recording, and a working cart-pole example with animation.

### Features

* added `graph()` method to BlockDiagram; export in DOT, Mermaid, GraphML, or ELK JSON -- a superset of `dotfile()` ([82495b0](https://github.com/petercorke/bdsim/commit/82495b03930ee4234620db1de6372f50016dd7dd))
* `graph()` gained a `mermaid_fenced` format and block shapes by block type ([ee2877a](https://github.com/petercorke/bdsim/commit/ee2877a9a0202ecb476967dca093540498da4db9))
* added a generic `ANIMATION` block with user-defined graphics setup and update ([d0779e2](https://github.com/petercorke/bdsim/commit/d0779e2894f0a228ff2420e3ea2be8ae79da5008))
* added a `--movie` option so graphics blocks can record an individual MP4, with optional on-frame timestamps ([3084aef](https://github.com/petercorke/bdsim/commit/3084aef1b6295560bb78d4e68cc62676396474af), [c71e3ea](https://github.com/petercorke/bdsim/commit/c71e3eaccc5a6b103bad8a279827e7a7eb4af717))
* animations and window tiling now work correctly in Jupyter/JupyterLite ([19a60fb](https://github.com/petercorke/bdsim/commit/19a60fb7ccda59ed9e3047cb7d310eb4c1a9179b))
* working cart-pole example with animation ([4769282](https://github.com/petercorke/bdsim/commit/47692823b8716368bcac09d93b4e739172d24a51), [e0d57a9](https://github.com/petercorke/bdsim/commit/e0d57a9cd15ec7bf63a8ea6406beefa063b3c827), [4c7c3b5](https://github.com/petercorke/bdsim/commit/4c7c3b53b2b21c40d4389ec696c17f3a190356e7))
* algebraic loop detection ([d5e41fe](https://github.com/petercorke/bdsim/commit/d5e41fe71fd7383fcf3182022fb58767cb1c5ae1))
* `__repr__` now displays inport, outport, and state names if present ([d8a1784](https://github.com/petercorke/bdsim/commit/d8a17847a83f74ecea9fca299a9039a9189728b6))
* connector blocks are hidden when a diagram is exported ([8e68f52](https://github.com/petercorke/bdsim/commit/8e68f52d97ee333ec7877747d9cdcac71008f97f))
* `sim.report(bd)`, with quieter output via `-q` ([76c9d27](https://github.com/petercorke/bdsim/commit/76c9d27ebf6bcd022916728177fc90d2191f0bb9))

### Bug Fixes

* fixed the `SCOPEXY` data cursor and its init chain ([65a4269](https://github.com/petercorke/bdsim/commit/65a42696ab289242424e3d7e2c9ff864c2d96e7a), [57db1e9](https://github.com/petercorke/bdsim/commit/57db1e9e823ae269ffb23712a58efb3254d1bc41))
* `SUM` returns a scalar rather than shape `(1,)` for circular wrapping modes ([3df56d8](https://github.com/petercorke/bdsim/commit/3df56d88c6238259daa80f2c15d2d75ea7258cae))
* `run_sim` now records scope data at every ODE step, not just interval endpoints ([8954090](https://github.com/petercorke/bdsim/commit/89540906ba16a10ffe2875d73a74a6956c4854e3))
* fixed a systematic error affecting stateful blocks ([3912034](https://github.com/petercorke/bdsim/commit/3912034dce886e3ec3e65fb84f55d7680f1b9839))
* fixed the `--tiles` option ([8a95258](https://github.com/petercorke/bdsim/commit/8a95258265c37b95a18f24c2e0a6231896961263))
* `BICYCLE` block arguments updated to match current Robotics Toolbox ([f85d465](https://github.com/petercorke/bdsim/commit/f85d465991113e70cd50c25d450ea2ad3e065aac))
* increased robustness to C-level crashes ([19f076c](https://github.com/petercorke/bdsim/commit/19f076cab1047d1278b5dbde9b4805be58487dca))
* `bdedit` robustness ([ac1586b](https://github.com/petercorke/bdsim/commit/ac1586b818a18c8e74fea78831a45b66f70afceb))

### Miscellaneous

* block renames and reorganisation, e.g. `POSEINTEGRATOR`/`POSEINTEGRATOR_D` moved to `blocks/spatial` ([4fa0c94](https://github.com/petercorke/bdsim/commit/4fa0c945acc513ebb2e1b90e61770eac8fab4469), [95cbc41](https://github.com/petercorke/bdsim/commit/95cbc41aeea2718f697c41d27d36aad0fd03bc10)); icons updated to match ([3dfdd69](https://github.com/petercorke/bdsim/commit/3dfdd69c6855985659b9588a26e5764e4df66f7c))

**Behaviour change:** `PROD`'s `matrix` argument was removed as redundant
(matrix vs elementwise operation is now auto-detected from input type) --
but the constructor was left to raise on an old `matrix=` argument rather
than accept and ignore it, breaking old saved diagrams
([e941531](https://github.com/petercorke/bdsim/commit/e94153187cd1c555cb4ba3b26f9d99d0759ae70f)).
Fixed in 1.3.0.


## [1.2.1](https://github.com/petercorke/bdsim/compare/v1.2.0...v1.2.1) (2026-05-11)

### Bug Fixes

* fixed `bdrun` ([bd84684](https://github.com/petercorke/bdsim/commit/bd8468437c800c5560b715a0a414a291dedacb1b))
* fixed `bdedit` load/save roundtrip error ([f5d0389](https://github.com/petercorke/bdsim/commit/f5d0389aeaebf88d4f3148708cf8cf0917912472))
* fixed JupyterLite working with an old version of bdsim ([c123423](https://github.com/petercorke/bdsim/commit/c1234239035717462c44ff85695ea5800cd3fbe8))
* fixed notebook URLs; zip files now built on every push ([4528e53](https://github.com/petercorke/bdsim/commit/4528e53c89f1ea057e724382ffd3c8d00c15d4f6))


1.2.0 May 2026

* Highlights
  - reworked integration engine to use solve_ivp from SciPy which supports events
  - more notebooks and examples
  - much faster dynamic block loading
  - type hinting throughout
  - bdedit reliability improved, now uses PySide6
  - massive use of CoPilot
  - runs in Jupyter and JupyterLite
  
* Code quality
  - more unit tests
  - comperehensive type hinting
  - reengineered supporting classes to build on native container classes
  - counters replaced by itertools.count
  - better repr and str functions
  - custom exceptions
  - all data attributes in Block are now protected (prefixed by _).  The only public attributes are set by block constructors.  This allows for discovery of parameters for possible run-time changing.

* Option handling
  - sys.argv passed through to user code
  - better -h display: use option grouping and subheadings
  - better argparse handling, use exclusive options to simplify
  - unused options are passed through to user code in sys.argv
  - attempt to catch mispelt options 

  * Runtime
  - lazy block loading, greatly speeds startup
  - better tracebacks for run-time errors
  - more options can be passed to integration engine
  - can save results to JSON

* Compile
  - wire errors include the file:linenum where the offending wire was created
  - scheduler now allows feedthrough blocks
  - reworked the algebraic loop detector, previously could miss a loop or recurse infinitely
  - depth option on report_summary

* Subsystem
  - can import .bd file as a subsystem

* bdload safety checks

* examples and notebooks

  - added cart pole demo
  - added bouncing ball demo to showcase EVENT block
  - lots more examples, with minimum documentation
  - set of notebooks that can be run in JupyterLite with animations

* Graphics
  - tiling, wide/tall options
  - tiles within a container window
  - data cursor
  - dark styling
  - MPL backend handling, works with %matplotlib in Jupyter
  - animations work in JupyterLite

* Integration engine
  - using `solve_ivp`
  - EVENT block
  - system state handling
  - context/simstate completely reengineered
  - periodic stops for compatability
  - reduce indirection in moving values from output port to input port, now use a PortValue object referred to by both ends.

* Blocks
  - EVENT uses the crossing-event machinery
  - STOP now uses the crossing-event machinery
  - ANIMATION block for simple custom graphics
  - added _safe methods
  - state handling x
  - continuous time
    - working DERIV and PID blocks
    - LTI_SISO supports various state space model structures
  - discrete time
    - mirror the full set of continuous time blocks (INTEG_S, DERIV_S, LTI_SS_S, LTI_SISO_S, POSEINTEGRATOR_S) + ZOH

* Testing
  - more testing
  - smoke tests for examples and notebooks

* bdedit
  - fix crashes, code changes, more exception catching
  - periodic saves, crash save
  - new block_library interface
  - uses PySide6 rather than PyQt.  More permissive licence.
  - 'V' will shift and scale the diagram to fill the canvas
  - uses new block_library interface
  - dialogs for export save
  - SVG output
  - handle dark/light themes
  - can be packaged as an app bundle.
