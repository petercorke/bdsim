
1.1.0 April 2026

* Highlights
  - bdedit reliability improved, now uses PySide6
  - reworked integration engine to use solve_ivp from SciPy which supports events
  - more notebooks and examples
  - much faster dynamic block loading
  - type hinting throughout
  - massive use of CoPilot
  
* Code quality
  - more unit tests
  - comperehensive type hinting
  - reengineered supporting classes to build on native container classes
  - counters replaced by itertools.count
  - better repr and str functions
  - custom exceptions
  - all data attributes in Block are now protected (prefixed by _).  The only public attributes are set by block constructors.  This allows for discovery of parameters for possible run-time changing.

* Runtime
  - sys.argv passed through to user code
  - better argparse handling, use exclusive options to simplify
  - lazy block loading, greatly speeds startup
  - better -h display
  - better tracebacks for run-time errors
  - more options can be passed to integration engine
  - can save results to JSON

* Compile
  - wire errors include the file:linenum where the offending wire was created
  - schedule allows feedthrough blocks
  - depth option on report_summary

* Subsystem
  - can import .bd file as a subsystem

* bdload safety checks

* Graphics
  - tiling, wide/tall options
  - tiles within a container window
  - data cursor
  - dark styling
  - MPL backend handling, works with %matplotlib in Jupyter

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
  - added _safe methods
  - state handling x
  - continuous time
    - working DERIV and PID blocks
    - LTI_SISO supports various state space model structures
  - discrete time
    - mirror the full set of continuous time blocks (INTEG_S, DERIV_S, LTI_SS_S, LTI_SISO_S, POSEINTEGRATOR_S) + ZOH

* Testing
  - smoke tests for examples

* bdedit
  - fix crashes, code changes, more exception catching
  - new block_library interface
  - uses PySide6 rather than PyQt.  More permissive licence.
  - 'V' will shift and scale the diagram to fill the canvas
  - uses block_library interface
  - dialogs for export save
  - SVG output
  - handle dark/light themes
  - distributed as an app bundle.
