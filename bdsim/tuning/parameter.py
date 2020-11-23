from numbers import Real
from collections import OrderedDict
from collections.abc import Iterable
from abc import ABC, abstractmethod
import numpy as np


class Param:
    """
    A parameter is a variable used by the block diagram that can be
    modified during the runtime of the engine. It is mostly used for
    real-time execution. Many methods of changing these parameters
    are provided with BDSim, from Qt Apps or over a ROS network via dynamic_reconfigure ROS params
    """
    def __new__(cls, val, **kwargs):
        "if val is already a param, update its unset attributes by kwargs, otherwise actually create a new Param"

        if isinstance(val, Param):
            if not issubclass(val.__class__, cls):
                # set the class so that super() doesn't complain when passing in a Param as a 'new NumParam' etc
                val.__class__ = cls
            return val
        else:
            # choose the correct paramtype based on the kwargs passed
            # always check for optionalparam first because it also has kwargs describing the underlying type
            param_cls = OptionalParam if 'default' in kwargs else \
                cls if cls is not Param else \
                EnumParam if 'oneof' in kwargs else \
                NumParam if _is_num(val) else \
                VecParam if _is_vectorlike(val) else \
                cls
            param = super().__new__(param_cls)

            # __init__ will not run after this unless param is of class cls,
            # For more specific param types such as RangeParam with 'default' in the kwargs,
            # the OptionalParam should wrap the RangeParam but doesn't get it's __init__ called, unless:
            if not isinstance(param, cls):
                # we do it manually
                param_cls.__init__(param, val, cls=cls, **kwargs)

            return param

    def __init__(
            self,
            val,
            *,  # force the use of keyword arguments
            name=None,
            on_change=None,
            created_by_user=False,
            **_kwargs):
        self.attrs = getattr(self, 'attrs', set())

        self.val = self.attr('val', val)
        self.name = self.attr('name', name)
        self.gui_attrs = self.attr('gui_attrs', set(('name',)))
        self.on_change_cbs = self.attr(
            'on_change_cbs', [on_change] if on_change else [])
        # if a new callback is being added
        if on_change is not None and on_change not in self.on_change_cbs:
            self.on_change(on_change)

        self.gui_reconstructor_cbs = self.attr('gui_reconstructor_cbs', [])
        self.created_by_user = self.attr('created_by_user', created_by_user)

        # this should only be added to in TunableBlock.param
        # list of (TunableBlock, arg_name: str) tuples
        self.used_in = self.attr('used_in', [])

    # TODO: potentially add validate()?

    def override(self, **kwargs):
        for attr, val in kwargs.items():
            if attr == 'on_change':
                self.on_change(val)
            else:
                setattr(self, attr, val)

    def full_name(self):
        return self.name or ', '.join('%s.%s' % (block, arg_name)
                                      for block, arg_name in self.used_in)

    # add a callback for val change
    def on_change(self, cb):
        # insert it to the start so that setup callbacks (called last) happen first
        self.on_change_cbs.insert(0, cb)

    # add a functional API too, to enable triggering with exclusions (to prevent infinite recursion)
    def set_val(self, val, exclude_cb=None):
        # coalesce single exclude_cb and multiple into tuple
        if not isinstance(exclude_cb, Iterable):
            exclude_cb = (exclude_cb, )

        if val is not self.val:  # only trigger if the value actually changed
            super().__setattr__('val', val)
            # copy the list so that if more cbs are added to self.on_change_cbs during
            # callback execution, they don't get run (leading to infinite callbacks)
            cbs = list(cb for cb in self.on_change_cbs if cb not in exclude_cb)
            for cb in cbs:
                cb(val)

    def __setattr__(self, attr, val):
        # don't trigger the callbacks on the first val 'set', but do on all others
        if attr == 'val' and hasattr(self, attr):
            self.set_val(val)
        else:
            super().__setattr__(attr, val)

            # gui_attrs may not exist in the first Param constructor call
            # pylint: disable=unsupported-membership-test
            if attr in getattr(self, 'gui_attrs', ()):
                self.reconstruct_gui()

    def reconstruct_gui(self):
        """
        Let the gui know that the sub_params have changed in such a way that
        the GUI controls must be reconstructed to reflect the sub_param structure
        """
        for cb in self.gui_reconstructor_cbs:
            cb(self)

    def register_gui_reconstructor(self, cb):
        """
        The gui registers a callback with this so that we can let it know if it must be rerendered
        """
        self.gui_reconstructor_cbs.append(cb)

    @ classmethod
    def map(cls, maybe_param, fn):
        "helper function to monad-map a variable that may or may not be a parameter"
        if isinstance(maybe_param, cls):
            maybe_param.val = fn(maybe_param.val)
        else:
            maybe_param = fn(maybe_param)

        return maybe_param

    def attr(self, attr, default):
        "returns attr if self has attr or it's none, otherwise return default"
        self.attrs.add(attr)
        val = getattr(self, attr, default)
        if val is None:
            val = default
        return val


class NumParam(Param):
    def __init__(self, val, min=None, max=None, step=None, log_scale=False, **kwargs):
        "step only works if log_scale is False, and only affects gui's"
        super().__init__(val, **kwargs)

        self.min = self.attr('min', min)
        self.max = self.attr('max', max)
        self.step = self.attr('step', step)
        self.log_scale = self.attr('log_scale', log_scale)

        assert self.min > 0 if self.log_scale else True, \
            "log_scaled parameters cannot have a value greater than 1"

        self.gui_attrs.update({'min', 'max', 'log_scale', 'step'})


class VecParam(NumParam):
    def __init__(self, val, min=None, max=None, **kwargs):
        super().__init__(val=np.array(val),
                         min=None if min is None else np.array(min),
                         max=None if max is None else np.array(max),
                         **kwargs)


class EnumParam(Param):
    def __init__(self, val, oneof=None, **kwargs):
        super().__init__(val, **kwargs)

        # TODO: support enums or dict mappings "choicename" -> value. Perhaps a bidict?
        self.oneof = self.attr('oneof', oneof)
        self.gui_attrs.update({'oneof'})


class HyperParam(Param, ABC):
    """
    A HyperParam is a parameter that is made up of a group of other parameters.
    Unlik Params, which are typically instantiated directly, HyperParam implementations should subclass this.
    Examples of a HyperParam could include a kernel object that could be a just an ndarray
    either a description (type, width, height), of which each is a parameter.
    """

    def __init__(self, val, **kwargs):
        super().__init__(val=None, **kwargs)

        # hyperparam setups can be intricate so better to hard reset these attrs every time
        # sub-parameters - shouldn't change after instantiation
        self.params = self.attr('params', OrderedDict())
        self.hidden = self.attr('hidden', set())
        self.gui_attrs.update({'hidden'})

        # bind the method to a single object so we can exclude it from param update recursion later
        # in python each self.func bound method is a different object so it can't
        # be checked for equality unless saved like so.
        # Need to think of a cleaner way to do this
        self.update = self.update  # I know this looks very strange, but it works

    # pylint: disable=method-hidden
    @ abstractmethod
    def update(self, _updated_val=None):
        pass

    def param(self, name, val, on_change=None, cls=Param, **kwargs):
        """
        Registers a sub-parameter for control generation.
        The order in which these are called determine the order of the GUI controls displayed.
        """
        # by default call the update function
        if not on_change:
            on_change = self.update

        if name in self.params:
            param = self.params[name]
        else:
            param = cls(val, **kwargs)
            # set this afterwards to avoid a callback after the initial self.val = ...
            param.on_change(on_change)
            param.on_change(lambda val: setattr(self, name, val))
            param.used_in.append((self.full_name(), name))
            self.params[name] = param

        return param.val

    def show_only(self, *params):
        self.show(*params)
        prev = self.hidden
        self.hidden = (prev - set(params)
                       ).union(set(p for p in self.params if p not in params))
        if prev != self.hidden:
            self.reconstruct_gui()

    def show(self, *params):
        prev = self.hidden
        self.hidden = prev - set(params)  # god I love python sometimes
        if prev != self.hidden:
            self.reconstruct_gui()

    def hide(self, *params):
        prev = self.hidden
        self.hidden = prev.union(set(params))
        if prev != self.hidden:
            self.reconstruct_gui()


class OptionalParam(HyperParam):
    # Expects a val that can be None. In a GUI, will be guarded by a checkbox

    def __init__(self, val, default=None, **kwargs):
        super().__init__(val, **kwargs)

        self.default = default
        self.enabled = self.param('enabled', val is not None)

        subvalue_kwargs = {k: v for k, v in kwargs.items(
        ) if k not in ('on_change', 'name', 'default')}
        self.enabled_value = self.param(
            'enabled_value', val if val else default, **subvalue_kwargs)
        self.update()

    def update(self, _=None):
        if self.enabled:
            self.show('enabled_value')
            self.val = self.enabled_value or self.default
        else:
            self.hide('enabled_value')
            self.val = None


class RangeParam(HyperParam):
    def __init__(self, val, min, max, step=None, log_scale=False, **kwargs):
        super().__init__(val, **kwargs)
        lower, upper = val if val else (None, None)
        shared_kwargs = dict(min=min, max=max, step=step, log_scale=log_scale)
        self.lower = self.param('lower', lower, **shared_kwargs)
        self.upper = self.param('upper', upper, **shared_kwargs)
        self.update()

    def update(self, _=None):
        self.val = self.lower, self.upper


def _is_vectorlike(x):
    return isinstance(x, np.ndarray) and x.ndim == 1 and np.issubdtype(x.dtype, np.number) \
        or isinstance(x, Iterable) and all(isinstance(x_i, Real) for x_i in x)


def _is_num(x):
    # bool is a real number too according to python, we don't want that
    return isinstance(x, Real) and not isinstance(x, bool)
