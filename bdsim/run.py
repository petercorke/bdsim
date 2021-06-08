# import numpy as np
# import bdsim
# import scipy.integrate as integrate
# import re



# # print a progress bar
# # https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
# def printProgressBar (fraction, prefix='', suffix='', decimals=1, length=50, fill = '█', printEnd = "\r"):

#     percent = ("{0:." + str(decimals) + "f}").format(fraction * 100)
#     filledLength = int(length * fraction)
#     bar = fill * filledLength + '-' * (length - filledLength)
#     print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)




# def progress(run):
#     if run.options.progress:
#         printProgressBar(run.t / run.T, prefix='Progress:', suffix='complete', length=60)


#     """

 
#     :ivar x: state vector
#     :vartype x: np.ndarray
#     :ivar T: maximum simulation time (seconds)
#     :vartype T: float
#     :ivar t: current simulation time (seconds)
#     :vartype t: float
#     :ivar fignum: number of next matplotlib figure to create
#     :vartype fignum: int
#     :ivar stop: reference to block wanting to stop simulation, else None
#     :vartype stop: Block subclass
#     :ivar checkfinite: halt simulation if any wire has inf or nan
#     :vartype checkfinite: bool
#     :ivar graphics: enable graphics
#     :vartype graphics: bool
#     """
    
# class RunState:

#     def __init__(self, name='main', **kwargs):
#         """

#         :param sysargs: process options from sys.argv, defaults to True
#         :type sysargs: bool, optional
#         :param graphics: enable graphics, defaults to True
#         :type graphics: bool, optional
#         :param animation: enable animation, defaults to False
#         :type animation: bool, optional
#         :param progress: enable progress bar, defaults to True
#         :type progress: bool, optional
#         :param debug: debug options, defaults to None
#         :type debug: str, optional
#         :param backend: matplotlib backend, defaults to 'Qt5Agg''
#         :type backend: str, optional
#         :param tiles: figure tile layout on monitor, defaults to '3x4'
#         :type tiles: str, optional
#         :raises ImportError: syntax error in block
#         :return: parent object for blockdiagram
#         :rtype: BlockDiagram
        
#         The instance has a number of factory methods that return instances of blocks.
        

        
#         The debug string comprises single letter flags:
            
#             - 'p' debug network value propagation
#             - 's' debug state vector
#             - 'd' debug state derivative 

#         """


#         self.x = None           # continuous state vector numpy.ndarray
#         self.T = None           # maximum.BlockDiagram time
#         self.t = None           # current time
#         self.fignum = 0
#         self.stop = None
#         self.checkfinite = True

#         self.debugger = True
#         self.name = name
#         self.debug_stop = False
#         self.t_stop = None  # time-based breakpoint



#         ##load modules from the blocks folder
#         self._load_blocks()
        

# def run(bd, T=10.0, dt=0.1, solver='RK45', 
#         block=False, checkfinite=True, minstepsize=1e-6, watch=[],
#         **kwargs):
#     """
#     Run the block diagram
    
#     :param T: maximum integration time, defaults to 10.0
#     :type T: float, optional
#     :param dt: maximum time step, defaults to 0.1
#     :type dt: float, optional
#     :param solver: integration method, defaults to ``RK45``
#     :type solver: str, optional
#     :param block: matplotlib block at end of run, default False
#     :type block: bool
#     :param checkfinite: error if inf or nan on any wire, default True
#     :type checkfinite: bool
#     :param minstepsize: minimum step length, default 1e-6
#     :type minstepsize: float
#     :param watch: list of input ports to log
#     :type watch: list
#     :param ``**kwargs``: passed to ``scipy.integrate``
#     :return: time history of signals and states
#     :rtype: Sim class
    
#     Assumes that the network has been compiled.
    
#     Graphics display in all blocks can be disabled using the `graphics`
#     option to the ``BlockDiagram`` instance.

#     ===================  =========  ========  ===========================================
#     Command line switch  Argument   Default   Behaviour
#     ===================  =========  ========  ===========================================
#     --nographics, -g     graphics   True      enable graphical display
#     --animation, -a      animation  False     update graphics at each time step
#     --noprogress, -p     progress   True      display simulation progress bar
#     --backend BE         backend    'Qt5Agg'  matplotlib backend
#     --tiles RxC, -t RxC  tiles      '3x4'     arrangement of figure tiles on the display
#     --debug F, -d F      debug      ''        debug flag string
#     ===================  =========  ========  ===========================================

    
#     Results are returned in a class with attributes:
        
#     - ``t`` the time vector: ndarray, shape=(M,)
#     - ``x`` is the state vector: ndarray, shape=(M,N)
#     - ``xnames`` is a list of the names of the states corresponding to columns of `x`, eg. "plant.x0",
#         defined for the block using the ``snames`` argument
#     - ``uN'` for a watched input where N is the index of the port mentioned in the ``watch`` argument
#     - ``unames`` is a list of the names of the input ports being watched, same order as in ``watch`` argument
    
#     If there are no dynamic elements in the diagram, ie. no states, then ``x`` and ``xnames`` are not
#     present.
    
#     The ``watch`` argument is a list of one or more input ports whose value during simulation
#     will be recorded.  The elements of the list can be:
#         - a ``Block`` reference, which is interpretted as input port 0
#         - a ``Plug`` reference, ie. a block with an index or attribute
#         - a string of the form "block[i]" which is port i of the block named block.
    
#     .. note:: Simulation stops if the step time falls below ``minsteplength``
#         which typically indicates that the solver is struggling with a very
#         harsh non-linearity.
#     """
    
#     assert bd.compiled, 'Network has not been compiled'


#     bd.T = T
#     bd.count = 0
#     bd.stop = None # allow any block to stop.BlockDiagram by setting this to the block's name
#     bd.checkfinite = checkfinite
#     if debug:
#         bd.debug_stop = True
#         bd.options.progress = False


#     # preproces the watchlist
#     watchlist = []
#     watchnamelist = []
#     re_block = re.compile(r'(?P<name>[^[]+)(\[(?P<port>[0-9]+)\])')
#     for n in watch:
#         if isinstance(n, str):
#             # a name was given, with optional port number
#             m = re_block.match(n)
#             name = m.group('name')
#             port = m.group('port')
#             b = bd.blocknames[name]
#             plug = b[port]
#         elif isinstance(n, Block):
#             # a block was given, defaults to port 0
#             plug = n[0]
#         elif isinstance(n, Plug):
#             # a plug was given
#             plug = n
#         watchlist.append(plug)
#         watchnamelist.append(str(plug))

#     # tell all blocks we're starting a BlockDiagram
#     bd.start()

#     if bd.ndstates == 0:
#         # no discrete time states
#         _run_until(bd, 0, T, dt, solver, 
#             block, checkfinite, minstepsize, debug, watchlist, kwargs)
#     else:
#         # find the first clock time
#         next = []
#         tprev = 0
#         for clock in bd.clocklist:
#             next.append(clock.next(tprev))  # append time of next sample
#             clock.x = clock.getstate0()  # get state of all blocks on this clock
        
#         # choose the nearest sample time
#         tnext = min(next)

#         while tnext <= T:
#             print(tnext)

#             # run system until next clock time
#             _run_until(bd, tprev, tnext, dt, solver, 
#                 block, checkfinite, minstepsize, debug, watchlist, kwargs)

#             tprev = tnext
#             for i, t in enumerate(next):
#                 if t == tnext:
#                     # it was this clock that ticked
#                     clock = bd.clocklist[i]

#                     # update the next time for this clock
#                     next[i] = clock.next(tprev)

#                     # get the new state
#                     clock._x = clock.getstate()

#                 tnext = min(next)

#     # pause until all graphics blocks close
#     bd.done(block=block)
#     # print(bd.count, ' integrator steps')

#     # return out
    
# def _run_until(bd, t0, T, dt=0.1, solver='RK45', 
#         block=False, checkfinite=True, minstepsize=1e-6, watch=[], debug=False, pluglist=None,
#         **kwargs):
#     try:
#         # get initial state from the stateful blocks


#         if bd.options.progress:
#             printProgressBar(0, prefix='Progress:', suffix='complete', length=60)

#         # out = scipy.integrate.solve_ivp.BlockDiagram._deriv, args=(self,), t_span=(0,T), y0=x0, 
#         #             method=solver, t_eval=np.linspace(0, T, 100), events=None, **kwargs)
#         if bd.nstates > 0:

#             x0 = bd.getstate0()
#             print('initial state x0 = ', x0)

#             # block diagram contains states, solve it using numerical integration

#             scipy_integrator = integrate.__dict__[solver]  # get user specified integrator

#             integrator = scipy_integrator(lambda t, y: bd.evaluate(y, t),
#                                             t0=t0, y0=x0, t_bound=T, max_step=dt, **kwargs)

#             # initialize list of time and states
#             tlist = []
#             xlist = []
#             plist = [[] for p in pluglist]
            
#             while integrator.status == 'running':

#                 # step the integrator, calls _deriv multiple times
#                 message = integrator.step()

#                 if integrator.status == 'failed':
#                     print(fg('red') + f"\nintegration completed with failed status: {message}" + attr(0))
#                     break

#                 # stash the results
#                 tlist.append(integrator.t)
#                 xlist.append(integrator.y)
                
#                 # record the ports on the watchlist
#                 for i, p in enumerate(pluglist):
#                     plist[i].append(p.block.inputs[p.port])
                
#                 # update all blocks that need to know
#                 bd.step()
                
#                 # update the progress bar
#                 if bd.options.progress:
#                     printProgressBar(integrator.t / T, prefix='Progress:', suffix='complete', length=60)

#                 # has any block called a stop?
#                 if bd.stop is not None:
#                     print(fg('red') + f"\n--- stop requested at t={bd.t:.4f} by {bd.stop:s}" + attr(0))
#                     break

#                 if minstepsize is not None and integrator.step_size < minstepsize:
#                     print(fg('red') + f"\n--- stopping on minimum step size at t={bd.t:.4f} with last stepsize {integrator.step_size:g}" + attr(0))
#                     break

#                 if bd.debug_stop:
#                     bd._debugger(integrator)

#             # save buffered data in a Struct
#             # out = Struct('results')
#             # out.t = np.array(tlist)
#             # out.x = np.array(xlist)
#             # out.xnames = bd.statenames
#             # for i, p in enumerate(pluglist):
#             #     out['u'+str(i)] = np.array(plist[i])
#             # out.unames = plugnamelist
#         else:
#             # block diagram has no states
            
#             # initialize list of time and states
#             tlist = []
#             plist = [[] for p in pluglist]
            
#             for t in np.arange(t0, T, dt):  # step through the time range

#                 # evaluate the block diagram
#                 bd.evaluate([], t)

#                 # stash the results
#                 tlist.append(t)
                
#                 # record the ports on the watchlist
#                 for i, p in enumerate(pluglist):
#                     plist[i].append(p.block.inputs[p.port])

#                 # update all blocks that need to know
#                 bd.step()

#                 # update the progress bar
#                 if bd.options.progress:
#                     printProgressBar(t / T, prefix='Progress:', suffix='complete', length=60)
                    
#                 # has any block called a stop?
#                 if bd.stop is not None:
#                     print('\n--- stop requested at t={:f} by {:s}'.format(bd.t, str(bd.stop)))
#                     break

#                 if bd.debug_stop:
#                     bd._debugger()
                
#             # # save buffered data in a Struct
#             # out = Struct('results')
#             # out.t = np.array(tlist)
#             # for i, p in enumerate(pluglist):
#             #     out['u'+str(i)] = np.array(plist[i])
#             # out.unames = plugnamelist
            
#         if bd.options.progress:
#             print('\r' + ' '* 90 + '\r')
            
#     except RuntimeError as err:
#         # bad things happens, print a message and return no result
#         print('unrecoverable error in evaluation: ', err)
#         raise

