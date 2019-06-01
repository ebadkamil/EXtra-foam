"""
Offline and online data analysis and visualization tool for azimuthal
integration of different data acquired with various detectors at
European XFEL.

XasCtrlWidget.

Author: Jun Zhu <jun.zhu@xfel.eu>, Ebad Kamil <ebad.kamil@xfel.eu>
Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
All rights reserved.
"""
from ..pyqtgraph import QtCore, QtGui

from .base_ctrl_widgets import AbstractCtrlWidget
from .smart_widgets import SmartBoundaryLineEdit, SmartLineEdit


class XasCtrlWidget(AbstractCtrlWidget):
    """Analysis parameters setup for pump-probe experiments."""

    _monochromators = [
        "",
        "SA3_XTD10_MONO/MDL/PHOTON_ENERGY",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__("XAS analysis setup", *args, **kwargs)

        self._reset_btn = QtGui.QPushButton("Reset")

        self._mono_src_cb = QtGui.QComboBox()
        for src in self._monochromators:
            self._mono_src_cb.addItem(src)

        self._n_bins_le = SmartLineEdit("60")
        self._n_bins_le.setValidator(QtGui.QIntValidator(1, 999))
        self._bin_range_le = SmartBoundaryLineEdit("0.7, 0.9")

        self.initUI()

        self.setFixedHeight(self.minimumSizeHint().height())

        self.initConnections()

    def initUI(self):
        """Overload."""
        layout = QtGui.QGridLayout()
        AR = QtCore.Qt.AlignRight

        layout.addWidget(QtGui.QLabel("Monochromator: "), 0, 0, AR)
        layout.addWidget(self._mono_src_cb, 0, 1, 1, 3)
        layout.addWidget(QtGui.QLabel("Bin range (keV): "), 1, 0, AR)
        layout.addWidget(self._bin_range_le, 1, 1)
        layout.addWidget(QtGui.QLabel("# of bins: "), 1, 2, AR)
        layout.addWidget(self._n_bins_le, 1, 3)
        layout.addWidget(self._reset_btn, 2, 3, AR)

        self.setLayout(layout)

    def initConnections(self):
        mediator = self._mediator

        self._reset_btn.clicked.connect(mediator.onXasReset)

        self._mono_src_cb.currentTextChanged.connect(
            mediator.onXasMonoSourceNameChange)

        self._n_bins_le.returnPressed.connect(
            lambda: mediator.onXasEnergyBinsChange(
                int(self._n_bins_le.text())))

        self._bin_range_le.value_changed_sgn.connect(
            mediator.onXasBinRangeChange)

    def updateMetaData(self):
        self._mono_src_cb.currentTextChanged.emit(
            self._mono_src_cb.currentText())

        self._n_bins_le.returnPressed.emit()

        self._bin_range_le.returnPressed.emit()

        return True
