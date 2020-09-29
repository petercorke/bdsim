from numbers import Real
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
                val.__class__ = cls  # set the class so that super() doesn't complain when passing in a Param as a 'new NumParam' etc
            return val
        else:
            # choose the correct paramtype based on the kweargs passed
            # always check for optionalparam first because it also has kwargs describing the underlying type
            ParamType = OptionalParam if 'default' in kwargs else \
                NumParam if _is_num(val) else \
                EnumParam if 'oneof' in kwargs else \
                VecParam if _is_vector(val) else \
                cls
            return super().__new__(ParamType)

    def __init__(
            self,
            val,
            *,  # force kwargs over positional args
            name=None,
            on_change=None,
            created_by_user=False,
            **_kwargs):
        "the real init, this way __new__ can choose whether or not to __init__"

        # if this is an existing param, (see __new__), only set unset stuff
        try:
            self.val = val if self.val is None else self.val
            self.name = self.name or name

            if on_change:
                self.on_change(on_change)

        except AttributeError:  # if the attribute doesn't exist it means this is a new param - init all

            self.val = val
            self.name = name
            self.gui_attrs = set(('name', ))
            self.on_change_cbs = [on_change] if on_change else []
            self.gui_reconstructor_cbs = []
            self.created_by_user = created_by_user

            # is should only be set in TunableBlock.param
            self.used_in = []  # list of (TunableBlock, arg_name: str) tuples

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
        # insert it to the start so that setup callbacks happen first
        self.on_change_cbs.insert(0, cb)

    # add a functional API too, to enable triggering with exclusions (to prevent infinite recursion)
    def set_val(self, val, exclude_cb=None):
        if val is not self.val:  # only trigger if the value actually changed
            super().__setattr__('val', val)
            for cb in self.on_change_cbs:
                if cb is not exclude_cb:
                    cb(val)

    def __setattr__(self, attr, val):
        if not hasattr(
                self, attr
        ):  # if the first time setting this, don't do anything special
            super().__setattr__(attr, val)
        elif attr == 'val':
            self.set_val(val)
        else:
            super().__setattr__(attr, val)

            if attr in self.gui_attrs:
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

    @classmethod
    def map(cls, maybe_param, fn):
        "helper function to monad-map a variable that may or may not be a parameter"
        if isinstance(maybe_param, cls):
            maybe_param.val = fn(maybe_param.val)
        else:
            maybe_param = fn(maybe_param)

        return maybe_param

    def attr(self, attr, default):
        "returns attr if self has attr or it's none, otherwise return default"
        return getattr(self, attr) \
            if hasattr(self, attr) and attr is not None \
            else default


class NumParam(Param):
    def __init__(self, val, min=None, max=None, log_scale=None, **kwargs):
        super().__init__(val, **kwargs)

        self.min = self.attr('min', min)
        self.max = self.attr('max', max)
        self.log_scale = self.attr('log_scale', log_scale)

        self.gui_attrs.update({'min', 'max', 'log_scale'})


class VecParam(NumParam):
    # displays differently to singular NumParam in the gui
    pass


class EnumParam(Param):
    def __init__(self, val, oneof=[], **kwargs):
        super().__init__(val, **kwargs)

        self.oneof = self.attr('oneof', oneof)
        self.gui_attrs.update({'oneof'})


class HyperParam(Param):
    """
    A HyperParam is a parameter that is made up of a group of other parameters.
    Unlik Params, which are typically instantiated directly, HyperParam implementations should subclass this.
    Examples of a HyperParam could include a kernel that can be instantiated fromkwar
    either a description (type, width, height), of which each is a parameter.
    """
    def __init__(self, val, **kwargs):
        super().__init__(val, **kwargs)

        # hyperparam setups can be intricate so better to hard reset these attrs every time
        self.params = {}  # sub-parameters
        self.hidden = set()

    def param(self, name, val, **kwargs):
        """
        Registers a sub-parameter for control generation.
        The order in which these are called determine the order of the GUI controls displayed.
        """
        param = Param(val, **kwargs)

        param.used_in.append((self.full_name(), name))

        if name not in self.params:
            self.params[name] = param

        return param

    def create_params(self, param_specs, **kwargs):
        """
        Helper function to create parameters,
        link their on_change callbacks to a setup function,
        then return the parameters.
        """
        return tuple(
            self.param(name, val, **kwargs) for name, val in param_specs)

    def show(self, *params):
        for param in params:
            try:
                self.hidden.remove(param)
            except KeyError:
                pass  # don't panic if it's already shown

    def hide(self, *params):
        for param in params:
            self.hidden.add(param)


class OptionalParam(HyperParam):
    # Expects a val that can be None. In a GUI, will be guarded by a checkbox

    def __init__(self, val, default, **kwargs):
        super().__init__(val, **kwargs)

        # remove kwargs that should'nt be passed down to the underlying value param
        for kw in ('on_change', 'name', 'default'):
            kwargs.pop(kw, None)

        self.default = default
        self.enabled = self.param('enabled', \
            val is not None, on_change=self._on_enabled_change)
        self._val = self.param('val', val, on_change=self.set_val, **kwargs)

    def _on_enabled_change(self, enabled):
        if enabled:
            self.val = self._val.val or self.default
        else:
            self.val = None


def _is_vector(x):
    # only accept numpy arrays to be vectors
    return isinstance(x, np.ndarray) and x.ndim == 1 \
        and np.issubdtype(x.dtype, np.number)


def _is_num(x):
    # bool is a real number too according to python, we don't want that
    return isinstance(x, Real) and not isinstance(x, bool)
