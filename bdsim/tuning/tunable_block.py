from abc import ABC
from bdsim.components import Block
from .parameter import Param


class TunableBlock(Block, ABC):
    # TODO: this could be merged into Block, if permitted
    def __init__(self, tinker=False, is_subblock=False, **kwargs):
        super().__init__(**kwargs)

        self.tinker = tinker
        self.is_subblock = is_subblock
        self.params = {}

    def param(self, name, val=None, **kwargs):
        """
        A user-facing function to get a reference to a parameter after this object's instantiation,
        and override any attrs with user-defined ones. This is the mutative alternative
        to first constructing a parameter via bd.param() and passing it in as an argument ie;

            >> num_param = bd.param(5, name='a number', min=0, max=10)
            >> block = bd.BLOCK(num_param=num_param)
        vs
            >> block = bd.BLOCK(num_param=0)
            >> # sets block.num_param.val = 5
            >> num_param = block.param('num_param', 5, name='a number', min=0, max=10)

        This parameter may then be reused in the constructor of other blocks as in the functional case

        Note: Some blocks may assign parameters to different names than its constructor arguments.
        """
        assert name in self.params, \
            ("Attempted to get param {name} which doesn't exist on block of class {classname}. Available params are {params}"
             "If calling from a TunableBloc constructor, you may be using self.param instead of self._param") \
            .format(name=name, classname=self.__class__.__name__, params=[self.params.keys()])

        self._param(name, val=val, created_by_user=True, **kwargs)

        return self.params[name]

    def _param(self, name, val, ret_param=False, **kwargs):
        """
        Creates a Param spec. If the user requested this directly (by passing in a Param for val):
            - add this block into it's param.used_in list,
            - adds it to self.params
            - setup callbacks from param value changing

        This function is expected to be called from any Block wishing to add parameters that may
        be reconfigured during runtime, perhaps via a gui or over a network. This function should
        be called with sensible defaults for the param in question that will aid in generating a gui.

        Returns the value of the parameter after any param constructor processing.
        It is expected to assign the return value of this function to self.name ie;

            def __init__(self, num_param=99):
                self.num_param = self._param('num_param', num_param, min=0, max=200)

        If ret_param is specified will return the Param object rather than it's val
        """
        # if the param already exists
        if name in self.params:
            # ensure the block constructor didn't accidentally double up on param defs
            if 'created_by_user' in kwargs:
                # override any user-set params
                param = self.params[name]
                if val is None:
                    param.override(**kwargs)
                elif isinstance(val, Param):
                    self.params[name] = param = Param(val, **kwargs)
                else:
                    param.override(val=val, **kwargs)
            else:
                assert name not in self.params, \
                    ("Assigning the same parameter to a block twice: {name}. This may be unintended. "
                     "If getting a reference to an existing param after block creation, use the block.param() method, not block._param()")\
                    .format(name=name)
        else:
            param = Param(val, **kwargs)
            self.params[name] = param

        # the val either needs to be created by bd.param() or tinker mode on,
        # then we should set it up to be functional in the gui
        if self.tinker or param.created_by_user:

            # don't double up on controls
            if param not in self.bd.gui_params:
                self.bd.gui_params.append(param)
            # bind the on_change handler
            param.on_change(lambda val: setattr(self, name, val))
            param.used_in.append((self, name))

        return param if ret_param else param.val
