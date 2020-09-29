from numbers import Real
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout, QComboBox, QPlainTextEdit
import numpy as np

from bdsim.tuning import HyperParam
from bdsim.tuning.parameter import HyperParam, NumParam, EnumParam, OptionalParam, VecParam
from bdsim.lib.qt_collapsible import Collapsible
from .tuner import Tuner


class QtTuner(Tuner, QWidget):
    def __init__(self, parameters, parent=None, title="BDSim Tuner"):
        Tuner.__init__(self, parameters, title)
        QWidget.__init__(self, parent)

        main_layout = QVBoxLayout(self)

        def on_vec_part_change(vec_param, label, slider, idx):
            # TODO: handle log scaling
            def on_change(val):
                try:  # if this was the result of a change elsewhere, pull out the scalar
                    val = val[idx]
                except TypeError:
                    pass  # otherwise assume val is a scalar

                # prevent ping-pong recursion with other scalar sliders in this vector
                if val != vec_param.val[idx]:
                    # do the update
                    vec_param.val[idx] = val
                    label.setText(str(val))
                    slider.setValue(val)
                    # trigger update for other callbacks
                    vec_param.set_val(vec_param.val, exclude_cb=on_change)

            # if something else changes the param too
            vec_param.on_change(on_change)
            return on_change

        def on_num_change(param, label, slider):
            # TODO: handle log scaling
            def on_change(val):
                label.setText(str(val))
                slider.setValue(val)
                # trigger update for other callbacks
                param.set_val(val, exclude_cb=on_change)

            # if something else changes the param too
            param.on_change(on_change)
            return on_change

        def create_trackbar(param,
                            on_change,
                            val=None,
                            min=None,
                            max=None,
                            **kwargs):

            wrapper = QWidget()
            layout = QHBoxLayout()
            val = val if val is not None else param.val
            label = QLabel(str(val))
            layout.addWidget(label)

            slider = QSlider(Qt.Horizontal)
            update = on_change(param, label, slider, **kwargs)
            slider.setValue(val)
            slider.setMinimum(min if min is not None else param.min)
            slider.setMaximum(max if max is not None else param.max)
            slider.valueChanged.connect(update)
            layout.addWidget(slider)

            wrapper.setLayout(layout)
            return wrapper

        def on_choice_change(param, combobox):
            def on_change(val):
                # coalesce into index (if triggered from Param.on_change)
                if val in param.oneof:
                    val = param.oneof.find(val)

                param.set_val(param.oneof(val), exclude_cb=on_change)
                combobox.setCurrentIndex(val)

            param.on_change(on_change)
            return on_change

        def on_text_change(param, textedit):
            def on_change(val):
                param.set_val(val, exclude_cb=on_change)
                textedit.setPlainText(val)

            param.on_change(on_change)
            return on_change

        for param in parameters:

            # must be checked before numparam for now as VecParam is a subclass of NumParam (for now)
            if isinstance(param, VecParam):
                collapsible = Collapsible(self, param.full_name())

                for idx, (scalar, min, max) in enumerate(
                        zip(param.val, param.min, param.max)):
                    collapsible.addWidget(
                        create_trackbar(param,
                                        on_vec_part_change,
                                        scalar,
                                        min,
                                        max,
                                        idx=idx))

                main_layout.addWidget(collapsible)

            elif isinstance(param, NumParam):
                main_layout.addWidget(QLabel(param.full_name()))
                main_layout.addWidget(create_trackbar(param, on_num_change))

            elif isinstance(param, EnumParam):
                val_i = param.oneof.index(param.val)
                assert val_i > -1, "param %s was not found to be oneof %s" % (
                    param.val, param.oneof)

                main_layout.addWidget(QLabel(param.full_name()))
                dropdown = QComboBox(self)
                dropdown.addItems(str(option) for option in param.oneof)
                dropdown.setCurrentIndex(val_i)
                dropdown.currentIndexChanged.connect(
                    on_choice_change(param, dropdown))

                main_layout.addWidget(dropdown)

            elif isinstance(param.val, str):
                main_layout.addWidget(QLabel(param.full_name()))
                textedit = QPlainTextEdit(param.val, self)
                textedit.textChanged.connect(on_text_change(param, textedit))

            elif isinstance(param, HyperParam):
                collapsible = Collapsible(self, param.full_name())
                # sub_tuner = QtTuner(param.params, self)

                # collapsible.addWidget(sub_tuner)
                main_layout.addWidget(collapsible)

            else:
                raise TypeError(
                    "Parameter %s of val %s (%s) does not match a Qt GUI control, yet needs tuning."
                    % (param.full_name(), param.val, type(param.val)))

        self.setLayout(main_layout)
        self.setWindowTitle(title)
        self.show()
