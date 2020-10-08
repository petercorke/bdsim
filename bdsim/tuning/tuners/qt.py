from abc import abstractmethod
import math
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, \
    QComboBox, QPlainTextEdit, QLayout, QCheckBox

from bdsim.tuning.parameter import HyperParam, NumParam, EnumParam, VecParam, Param, OptionalParam
from .qt_collapsible import Collapsible
from .tuner import Tuner


def _val_str(val):
    "keep it under 7 characers. If too large start using sci-notation"
    val_str = str(val)
    return val_str[:6] if abs(val) > 0.001 and abs(val) < 10000 else \
        '%.2g' % val if len(val_str) > 6 else \
        val_str


def _create_slider(parent: QWidget, min, max, val, on_change, log_scale, step):
    slider_wrapper = QWidget(parent)
    wrapper_layout = QHBoxLayout(slider_wrapper)
    wrapper_layout.setContentsMargins(0, 0, 0, 0)
    slider_wrapper.setLayout(wrapper_layout)
    label = QLabel(_val_str(val), parent)
    label.setStyleSheet('min-width: 55px; margin: 0px;')
    wrapper_layout.addWidget(label)

    slider = QSlider(Qt.Horizontal, slider_wrapper)
    slider.setStyleSheet('min-width: 150px;')
    wrapper_layout.addWidget(slider)

    if log_scale:
        slider.setMinimum(0)
        slider.setMaximum(100)
        log_offset = min - 1  # make sure it's min when slider val == 0
        # make sure it's max when slider val == 100
        log_base = (max - log_offset)**(1 / 100)
        log = (log_base, log_offset)

    else:
        # TODO: ensure that this rounding doesn't cause problems
        slider.setMinimum(round(min / step))
        slider.setMaximum(round(max / step))
        log = None

    val = _rescale_slider_val(val, log, step, reverse=True)
    slider.setValue(val)

    slider.valueChanged.connect(on_change)
    return slider, label, log, slider_wrapper


def _rescale_slider_val(val, log, step, reverse=False):
    if log:
        (base, offset) = log
        return math.log(val - offset, base) if reverse \
            else base ** val + offset
    else:
        return val / step if reverse else val * step


def _clear_layout(layout):
    # kudos to TheTrowser: https://stackoverflow.com/questions/37564728/pyqt-how-to-remove-a-layout-from-a-layout/37575246#37575246
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
            if isinstance(widget, QtTuner.ParamEditor):
                widget.cleanup()
            # widget.deleteLater()
            # widget.destroyed.connect(lambda widget: widget.__del__())
            # sleep to let the Qt event loop run and actually perform the deletion
        else:
            _clear_layout(item.layout())


class QtTuner(Tuner, QWidget):

    class ParamEditor(QWidget):
        def __init__(self, param: Param, parent: QWidget):
            super().__init__(parent)

            self.param = param
            # bind the method to a constant python obj so we can remove it
            # later upon __del__ (when gui_reconstruction causes this to go hidden)
            self.on_param_change = self.on_param_change
            self.param.on_change(self.on_param_change)

            def gui_reconstructor(_param):
                _clear_layout(self._layout)
                self.setup()

            self.param.register_gui_reconstructor(gui_reconstructor)
            self._layout = QVBoxLayout(self)
            self._layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self._layout)
            self.setup()

        @abstractmethod
        def setup(self):
            pass

        # pylint: disable=method-hidden
        @abstractmethod
        def on_param_change(self, val):
            pass

        def cleanup(self):
            self.param.on_change_cbs.remove(self.on_param_change)

    class NumEditor(ParamEditor):
        def setup(self):
            p = self.param  # for brevity

            self._layout.addWidget(QLabel(p.full_name(), self))

            self.slider, self.label, self.log, slider_wrapper = _create_slider(
                self, p.min, p.max, p.val, self.on_slider_change, p.log_scale, p.step)

            self._layout.addWidget(slider_wrapper)

        def on_slider_change(self, val):
            val = _rescale_slider_val(val, self.log, self.param.step)
            self.label.setText(_val_str(val))
            # trigger update for other callbacks
            self.param.set_val(val, exclude_cb=self.on_param_change)

        def on_param_change(self, val):
            self.label.setText(_val_str(val))
            val = _rescale_slider_val(
                val, self.log, self.param.step, reverse=True)
            self.slider.setValue(val)

    class VecEditor(ParamEditor):

        def setup(self):
            p = self.param
            collapsible = Collapsible(title=p.full_name(), parent=self)
            self._layout.addWidget(collapsible)

            self.sliders = []

            for idx, (val, min, max) in enumerate(zip(p.val, p.min, p.max)):
                slider, label, log, slider_wrapper = _create_slider(
                    self, min, max, val, self.get_on_slider_change(
                        idx), p.log_scale, p.step
                )
                self.sliders.append((slider, label, log))
                collapsible.addWidget(slider_wrapper)

        def get_on_slider_change(self, idx):
            def on_slider_change(val):
                _slider, label, log = self.sliders[idx]
                val = _rescale_slider_val(val, log, self.param.step)
                label.setText(_val_str(val))
                # do the update
                # use a new vec/list to actually trigger callbacks in self.param.set_val
                new_vec = self.param.val.copy()
                new_vec[idx] = val
                # trigger update for external callbacks
                self.param.set_val(
                    new_vec, exclude_cb=self.on_param_change)
            return on_slider_change

        def on_param_change(self, val):
            for scalar, (slider, label, log) in zip(val, self.sliders):
                label.setText(_val_str(scalar))
                scalar = _rescale_slider_val(scalar, log, self.param.step)
                slider.setValue(scalar)

    class Dropdown(ParamEditor):

        def setup(self):
            self._layout.addWidget(QLabel(self.param.full_name(), self))

            self.dropdown = QComboBox(self)
            self.dropdown.addItems(str(option) for option in self.param.oneof)
            self.dropdown.setCurrentIndex(
                self.param.oneof.index(self.param.val))
            self.dropdown.currentIndexChanged.connect(self.on_dropdown_changed)
            self._layout.addWidget(self.dropdown)

        def on_param_change(self, val):
            self.dropdown.setCurrentIndex(self.param.oneof.index(val))

        def on_dropdown_changed(self, idx):
            self.param.set_val(
                self.param.oneof[idx], exclude_cb=self.on_param_change)

    class TextInput(ParamEditor):
        def setup(self):
            self._layout.addWidget(QLabel(self.param.full_name(), self))
            self.textedit = QPlainTextEdit(self.param.val, self)
            self.textedit.textChanged.connect(self.on_textedit_change)
            self.textedit.setStyleSheet('max-height: 26px;')
            self._layout.addWidget(self.textedit)

        def on_param_change(self, val):
            self.textedit.setPlainText(val)

        def on_textedit_change(self):
            self.param.set_val(self.textedit.toPlainText(),
                               exclude_cb=self.on_param_change)

    class Checkbox(ParamEditor):
        def setup(self):
            self.checkbox = QCheckBox(self.param.full_name(), self)
            self.checkbox.setChecked(self.param.val)
            self.checkbox.toggled.connect(lambda checked: self.param.set_val(
                checked, exclude_cb=self.on_param_change))
            self._layout.addWidget(self.checkbox)

        def on_param_change(self, val):
            self.checkbox.setChecked(val)

    class HyperParamEditor(ParamEditor):

        def __init__(self, *args, **kwargs):
            self.collapsible = None
            self.sub_tuner = None
            super().__init__(*args, **kwargs)

        def setup(self):
            # retain open/close state during reconstruction
            start_collapsed = self.collapsible.is_collapsed if self.collapsible else True
            self.collapsible = Collapsible(
                self.param.full_name(), self, collapsed=start_collapsed)

            # if OptionalParam and val is hyperparam, pull the value params up to reduce unnecessary gui nesting
            if isinstance(self.param, OptionalParam) and isinstance(self.param.params['enabled_value'], HyperParam):
                params = self.param.params
                hyperparam = params['enabled_value']
                sub_tuner_params = [params['enabled']]
                if self.param.enabled:
                    sub_tuner_params.extend(
                        p for k, p in hyperparam.params.items() if k not in hyperparam.hidden)
            else:
                sub_tuner_params = [
                    p for k, p in self.param.params.items() if k not in self.param.hidden]

            self.sub_tuner = QtTuner(sub_tuner_params, self)

            self.collapsible.addWidget(self.sub_tuner)
            self._layout.addWidget(self.collapsible)

        def on_param_change(self, _val=None):
            pass  # explicit pass - the subtuner will handle everything

        def cleanup(self):
            super().cleanup()
            self.sub_tuner.cleanup()

    def __init__(self, parameters, parent=None, title="BDSim Tuner"):
        Tuner.__init__(self, parameters, title)
        QWidget.__init__(self, parent)
        self.editors = []

        self.setup_gui()

    def setup_gui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSizeConstraint(QLayout.SetFixedSize)

        for param in self.parameters:
            editor_cls = QtTuner.VecEditor if isinstance(param, VecParam) else \
                QtTuner.NumEditor if isinstance(param, NumParam) else \
                QtTuner.Dropdown if isinstance(param, EnumParam) else \
                QtTuner.HyperParamEditor if isinstance(param, HyperParam) else \
                QtTuner.TextInput if isinstance(param.val, str) else \
                QtTuner.Checkbox if isinstance(param.val, bool) else None
            assert editor_cls, \
                "Parameter %s of val %s from %s does not match a Qt GUI control, yet needs tuning." \
                % (param.full_name(), param.val, param)

            editor = editor_cls(param, self)
            self.editors.append(editor)
            main_layout.addWidget(editor)

        self.setLayout(main_layout)
        self.setWindowTitle(self.title)
        self.show()

    def cleanup(self):
        for editor in self.editors:
            editor.cleanup()
        self.editors = []

    def __del__(self):
        self.cleanup()
