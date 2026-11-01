# Changelog

## [1.5.0](https://github.com/petercorke/bdsim/compare/v1.4.1...v1.5.0) (2026-11-01)


### Features

* --npz writes the results as a NumPy archive ([#154](https://github.com/petercorke/bdsim/issues/154)) ([6ee2a19](https://github.com/petercorke/bdsim/commit/6ee2a193232d5b995021d851af203e799146b3dd))
* a list of numbers becomes an ndarray by default, with asarray=False to opt out ([dd55a75](https://github.com/petercorke/bdsim/commit/dd55a7573adbb305b210159b5cfe06d1cc6d1843))
* a list of numbers becomes an ndarray by default; asarray=False to opt out ([93bef9d](https://github.com/petercorke/bdsim/commit/93bef9d1c8bfe4378270a0d80cac9a75f366d304))
* add Sqrt, Sign, Abs and Deadband function blocks ([#178](https://github.com/petercorke/bdsim/issues/178)) ([e89e173](https://github.com/petercorke/bdsim/commit/e89e173363e2d57f844c08f9fb04ab9d7a374ea5))
* add the Block.configure() hook, run once per run before start() ([70656dc](https://github.com/petercorke/bdsim/commit/70656dc5b0e6f703605b7ac2d05a324acdac5357))
* block parameters: one registry, type enforcement, --set and --param ([dee08f6](https://github.com/petercorke/bdsim/commit/dee08f6ada5c72d7fbdd1f5f354231bb84570fa3))
* block parameters: one registry, type enforcement, --set and --param ([4c64920](https://github.com/petercorke/bdsim/commit/4c649209f25f701f09acfe516e40ffdaac0587db))
* initial states are parameters, and --set is applied before they are collected ([4646bf2](https://github.com/petercorke/bdsim/commit/4646bf21e5adeda1063c2b43db4bc6a6dd7785ff))
* NumPy dtype literals for parameters given as text, float32([1, 2]) ([#157](https://github.com/petercorke/bdsim/issues/157)) ([8a04025](https://github.com/petercorke/bdsim/commit/8a040258f1e4b1df224d2e4aba1f12ee5fbfe499))
* NumPy dtype literals for parameters given as text: float32([1, 2]), uint16(5) ([8a04025](https://github.com/petercorke/bdsim/commit/8a040258f1e4b1df224d2e4aba1f12ee5fbfe499))
* one switch for the run-time checks, and a check for change of signature ([c6de015](https://github.com/petercorke/bdsim/commit/c6de01568c478f9ee4512ed70ce96afad005f00c))
* one switch for the run-time checks, and a check for change of signature ([615a924](https://github.com/petercorke/bdsim/commit/615a9241e38c7e7098becde6b8f192a7510786a1))
* PID and PID_S take terms= to say which terms to build; fixes pure P ([#163](https://github.com/petercorke/bdsim/issues/163)) ([b4b5f01](https://github.com/petercorke/bdsim/commit/b4b5f010f03563b3e8577db6b029a5692c5e7b8a))
* properties and forwarding for every block parameter ([f5b58c3](https://github.com/petercorke/bdsim/commit/f5b58c3e6ddb2e27f02d9619df9603574035cd31))
* properties for the parameters of single blocks with derived state ([4b0def1](https://github.com/petercorke/bdsim/commit/4b0def1b39a0165a7625ca044cd0efdd5ae092af))
* record the signature of every wire at compile time ([6eb8240](https://github.com/petercorke/bdsim/commit/6eb82403491cd1bd6fd107f0315839aceba6886f))
* record wire signatures at compile time; Block.configure(); reset() restores block state ([dea411d](https://github.com/petercorke/bdsim/commit/dea411db491eb8f4b851129617792403f69462cc))
* replace subsystem INPORT/OUTPORT blocks by wires (fixes [#84](https://github.com/petercorke/bdsim/issues/84)) ([32a259f](https://github.com/petercorke/bdsim/commit/32a259f933b9a7900a29506acac5cc007650b755))
* replace the INPORT and OUTPORT blocks of a subsystem by wires ([#84](https://github.com/petercorke/bdsim/issues/84)) ([ed7e5fe](https://github.com/petercorke/bdsim/commit/ed7e5fedb12c5316a4373c077b48c3434b4f5e0b))
* source blocks emit one type, checked when the block is created ([6cccba5](https://github.com/petercorke/bdsim/commit/6cccba50187e281affea64b5c9421efe5bc94f99))
* source blocks emit one type, checked when the block is created ([a390432](https://github.com/petercorke/bdsim/commit/a390432fc7f0bae61ca71b810415962ab926ab23))
* subsystem blocks forward their parameters to the blocks inside ([1695667](https://github.com/petercorke/bdsim/commit/1695667701c5e107e156f0d28b5a0b2f9986721c))


### Bug Fixes

* a crossing event with a fixed output grid restarts at the event time ([#159](https://github.com/petercorke/bdsim/issues/159)) ([e95592b](https://github.com/petercorke/bdsim/commit/e95592bd945a79fc4466c70ff731735bb8c5a1e4))
* avoid endless repainting when setting background brush in bdedit ([#145](https://github.com/petercorke/bdsim/issues/145)) ([b6e23a0](https://github.com/petercorke/bdsim/commit/b6e23a0e25945d3ce090ce446b9107de3f598bc5))
* **bdedit:** render the screenshot region for PNG export ([#142](https://github.com/petercorke/bdsim/issues/142)) ([0d51208](https://github.com/petercorke/bdsim/commit/0d5120844363a02aa7c378ef7970bc6a5f56f9fc))
* give subsystem instances unique default names, and stop defaulting the diagram name to "main" ([0540805](https://github.com/petercorke/bdsim/commit/0540805522d56d11bb0ff8fa25cfab3cfed2137e))
* Scope no longer passes the line style to matplotlib as its label ([#147](https://github.com/petercorke/bdsim/issues/147)) ([ea5084a](https://github.com/petercorke/bdsim/commit/ea5084a3f9ec4bbc20f84d0ad3b40538a97e3333))
* Slice1 accepts an integer index as documented; drop a debug print in Function.start ([af9202b](https://github.com/petercorke/bdsim/commit/af9202bb1619bd29b97e7b0dcd5c5681f0d7e0ac))
* unique default names for subsystem instances; diagram name defaults to None ([#148](https://github.com/petercorke/bdsim/issues/148)) ([0540805](https://github.com/petercorke/bdsim/commit/0540805522d56d11bb0ff8fa25cfab3cfed2137e))


### Documentation

* correct the Pow matrix and Scope scale parameter descriptions ([c0e7adc](https://github.com/petercorke/bdsim/commit/c0e7adcd992c23334491773c9e840a8320466402))
* say that supported Python versions are those in the pyproject classifiers ([#173](https://github.com/petercorke/bdsim/issues/173)) ([b01dab2](https://github.com/petercorke/bdsim/commit/b01dab22e5a701bf13c7aee9776b8721bf98c185))

## [1.4.1](https://github.com/petercorke/bdsim/compare/v1.4.0...v1.4.1) (2026-10-19)

### Highlights

* Codacy code quality A
* Scope blocks maintain data at full temporal resolution, only subsample for display
* New icons
* Remove cruft from the shipped package (the source distribution drops from 6.2 MB to 0.7 MB)
* Migrate from black/flake8 to ruff


### Features

* **icons:** add cast.png icon for the CAST block ([f7b1b39](https://github.com/petercorke/bdsim/commit/f7b1b393a3a4251f5ff1457dabaf4ddf57194c92))
* **icons:** add icons for hardware I/O blocks ([c36273a](https://github.com/petercorke/bdsim/commit/c36273acf6ec681179ea553614a1019cbdd85257))


### Bug Fixes

* allow block diagrams without loading the block library ([546e1d5](https://github.com/petercorke/bdsim/commit/546e1d5e0f0044bd9804cd52e271c79a96460883))
* apply functools.wraps in oodebug so operator signatures survive introspection ([#121](https://github.com/petercorke/bdsim/issues/121)) ([ad38132](https://github.com/petercorke/bdsim/commit/ad3813280b39e9566b075a6a8db40a23007f68ab))
* apply Qt5Agg's animation refresh path to QtAgg too ([90b130a](https://github.com/petercorke/bdsim/commit/90b130a7f8f11ed87cadeb279cd32611f7815c40))
* apply Qt5Agg's flush_events()+draw() animation refresh to QtAgg too ([b287bd0](https://github.com/petercorke/bdsim/commit/b287bd06277d6be435c2898b00b4ebfa93539296))
* apply safe ruff F-rule fixes; ignore F401 in bdedit ([7882a21](https://github.com/petercorke/bdsim/commit/7882a2168917690249d9772bf529c36daef6294f))
* BDSim.done()/closefigs() duplicate definitions, silent test gap ([b305262](https://github.com/petercorke/bdsim/commit/b305262d45a4edcb7c6bd79896d59f28cc408b21))
* BDSim.done()/closefigs() were defined twice, silently losing notebook support ([9a540ac](https://github.com/petercorke/bdsim/commit/9a540ac111444b97b4a4c39e876d9bd4677d16b1))
* block discovery no longer crashes on docstrings without :type: lines ([#133](https://github.com/petercorke/bdsim/issues/133)) ([f649053](https://github.com/petercorke/bdsim/commit/f649053d13f204b61ed8678c3a0ff6fda17e7cea))
* clean up unused locals and dead code flagged by pyflakes ([4134141](https://github.com/petercorke/bdsim/commit/4134141ad3fa24a6201890e7728fc320f9f5dba3))
* clean up unused locals and dead code flagged by pyflakes (F841/F811/F541/F999) ([823a9e0](https://github.com/petercorke/bdsim/commit/823a9e0441d25671857bd69f667de7966c54254a))
* drop unnecessary `global clocklist` in test_components.py ([5883df7](https://github.com/petercorke/bdsim/commit/5883df704a295ff7298de85f8a163818348a3ca8))
* exclude internal-state invariant guards from coverage measurement ([888ffae](https://github.com/petercorke/bdsim/commit/888ffae7e199e4770d328ba054f0bede177e386d))
* **icons:** drop doubled backslash before \! kerning in pose icons ([cacbe8b](https://github.com/petercorke/bdsim/commit/cacbe8b8e25c55ebb25694aceff8f32d8844f5f9))
* make bdtex2icon fail fast and clearly instead of hanging/silent ([4759170](https://github.com/petercorke/bdsim/commit/475917035ecc5728ac77751fd8f1390273f44d24))
* make block-factory stub bodies raise instead of falling through to None ([0b2c14c](https://github.com/petercorke/bdsim/commit/0b2c14c87fcc3bd10543124116c10a26262af3a6))
* make block-factory stub bodies raise instead of falling through to None ([cf8cc93](https://github.com/petercorke/bdsim/commit/cf8cc933743c826522fd3109a025f1c2a3978ccc))
* omit the generated stub file from coverage measurement ([6c3e382](https://github.com/petercorke/bdsim/commit/6c3e3829cb49bcf7e175a6bbb8bd05af7c02f21c))
* place nosemgrep suppressions on the exact flagged lines ([e503aed](https://github.com/petercorke/bdsim/commit/e503aed49b39c530ce54a190696379d60dfafa50))
* point bdtex2icon entry point at bdedit.tex2icon ([ec9c069](https://github.com/petercorke/bdsim/commit/ec9c069c065a9f2cacbdc1c49ae44558e62d539c))
* record Scope data at full simulation resolution, not throttled ~200 samples ([10a0911](https://github.com/petercorke/bdsim/commit/10a09112fce0434d4a30ad647ef58a9063d47efd))
* record Scope data at full simulation resolution, not throttled ~200 samples ([4de3370](https://github.com/petercorke/bdsim/commit/4de3370f2a30569d8a3a6945781d6cab56d96385))
* repair the bdtex2icon icon pipeline and serve icons locally in docs ([c5bd523](https://github.com/petercorke/bdsim/commit/c5bd523cf14acc91dbaaac34e0b8c16748dade14))
* replace validation asserts with explicit exceptions (Bandit B101) ([39d87bc](https://github.com/petercorke/bdsim/commit/39d87bc1844096b917a992bb68ebec7079b24cc9))
* replace validation asserts with explicit exceptions (Bandit B101) ([f4126ff](https://github.com/petercorke/bdsim/commit/f4126fffd57498047d692701c83037b39ac90bb2))
* resolve subprocess executables via shutil.which, justify remaining findings ([835daf1](https://github.com/petercorke/bdsim/commit/835daf1a9b05a135b4fb6b88d7822055bf1101a9))
* serve block icons locally from the Sphinx build, not a stale remote URL ([4849b61](https://github.com/petercorke/bdsim/commit/4849b61913afa9ba7008c10d5042e92729e0ea4b))
* split the two subprocess nosemgrep suppressions onto their own lines ([b11d8a2](https://github.com/petercorke/bdsim/commit/b11d8a21eb5883b7bc370a1d4285a8dadcc4bd08))
* use pragma: no cover instead of omitting the whole stub file ([72cba39](https://github.com/petercorke/bdsim/commit/72cba39de5e68316c2625cae87a73da59622f905))


### Documentation

* add Codacy grade badge to README ([b7430bf](https://github.com/petercorke/bdsim/commit/b7430bf4bde7f3286dec9951e6418a73a2e4ba59))
* add sphinx-copybutton and sphinx-codeautolink ([2ab0b03](https://github.com/petercorke/bdsim/commit/2ab0b038ae8df44901ac5de8ba64ba59e4da7c79))
* add sphinx-copybutton and sphinx-codeautolink extensions and config ([c4a5a2d](https://github.com/petercorke/bdsim/commit/c4a5a2d382e926057fe3015323fa5565ce28eb74))
* add sphinx-copybutton and sphinx-codeautolink to docs deps ([4fdcaed](https://github.com/petercorke/bdsim/commit/4fdcaed3d48a6d1842ffbdec7c0551eb9835b455))
* ask contributors to check for existing PRs and claim issues first ([#125](https://github.com/petercorke/bdsim/issues/125)) ([120aece](https://github.com/petercorke/bdsim/commit/120aece6001229366e3ff9d94f4b293259a70ecc))
* document the code-generated icon method, fix stale links ([46fc476](https://github.com/petercorke/bdsim/commit/46fc4765e48edfe6b6a61a3fd1f1c11e9e3d3db9))
* include the bdsim wiki in llms.txt and llms-full.txt ([7e5b2c9](https://github.com/petercorke/bdsim/commit/7e5b2c9e1e00499e84d076df1feec74bcec0335c))
* point each agent file at the other's audience ([#108](https://github.com/petercorke/bdsim/issues/108)) ([a955ac3](https://github.com/petercorke/bdsim/commit/a955ac37d0456209e3471b6c5e8a08976fc36d70))
* publish llms.txt and llms-full.txt with the documentation site ([b1154d6](https://github.com/petercorke/bdsim/commit/b1154d64ece6b60efe66be733873fbc1490d597a))
* rewrite CONTRIBUTING.md ([57ade75](https://github.com/petercorke/bdsim/commit/57ade75520d040afcf940387f64bbf6d33dd0345))
* say what happens to the factory methods when the block library is not loaded ([6301163](https://github.com/petercorke/bdsim/commit/63011630a4456fdcec9f074f692fb7637fbac45d))
* update AGENTS.md for feat/bdweb and drop stale feat/shiftop note ([#119](https://github.com/petercorke/bdsim/issues/119)) ([297c948](https://github.com/petercorke/bdsim/commit/297c9480ec1900e2b4b2504f47a2abb81212164f))


### Build System

* configure ruff (format + F rules) in place of black and flake8 ([38ce97f](https://github.com/petercorke/bdsim/commit/38ce97fb36105c15b42ce752fa5847dfbbbd8864))
* exclude bdedit's documentation figures from the sdist ([86c5315](https://github.com/petercorke/bdsim/commit/86c531504520546d36e43b5f862c2b400c6e87cd))

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
