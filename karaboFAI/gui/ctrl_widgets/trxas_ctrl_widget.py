"""
Offline and online data analysis and visualization tool for azimuthal
integration of different data acquired with various detectors at
European XFEL.

Author: Jun Zhu <jun.zhu@xfel.eu>
Copyright (C) European X-Ray Free-Electron Laser Facility GmbH.
All rights reserved.
"""
from PyQt5 import QtCore, QtGui, QtWidgets

from .base_ctrl_widgets import _AbstractCtrlWidget
from .smart_widgets import SmartBoundaryLineEdit, SmartLineEdit


_DEFAULT_N_BINS = "10"
_DEFAULT_BIN_RANGE = "0, 1e9"
_MAX_N_BINS = 9999


class TrXasCtrlWidget(_AbstractCtrlWidget):
    """Analysis parameters setup for ROI analysis."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._delay_device_le = SmartLineEdit("Any")
        self._delay_ppt_le = SmartLineEdit("timestamp.tid")

        # self._energy_device_le = SmartLineEdit("SA3_XTD10_MONO/MDL/PHOTON_ENERGY")
        # self._energy_ppt_le = SmartLineEdit("actualEnergy")
        self._energy_device_le = SmartLineEdit("Any")
        self._energy_ppt_le = SmartLineEdit("timestamp.tid")

        self._delay_range_le = SmartBoundaryLineEdit(_DEFAULT_BIN_RANGE)
        self._n_delay_bins_le = SmartLineEdit(_DEFAULT_N_BINS)
        self._n_delay_bins_le.setValidator(
            QtGui.QIntValidator(1, _MAX_N_BINS))

        self._energy_range_le = SmartBoundaryLineEdit(_DEFAULT_BIN_RANGE)
        self._n_energy_bins_le = SmartLineEdit(_DEFAULT_N_BINS)
        self._n_energy_bins_le.setValidator(
            QtGui.QIntValidator(1, _MAX_N_BINS))

        self._reset_btn = QtWidgets.QPushButton("Reset")

        self.initUI()
        self.initConnections()

    def initUI(self):
        """Overload."""
        QLabel = QtWidgets.QLabel
        layout = QtGui.QGridLayout()
        AR = QtCore.Qt.AlignRight

        i_row = 0
        layout.addWidget(QLabel("Delay device ID: "), i_row, 0, AR)
        layout.addWidget(self._delay_device_le, i_row, 1, 1, 3)

        i_row += 1
        layout.addWidget(QLabel("Delay device property: "), i_row, 0, AR)
        layout.addWidget(self._delay_ppt_le, i_row, 1, 1, 3)

        i_row += 1
        layout.addWidget(QLabel("Mono device ID: "), i_row, 0, AR)
        layout.addWidget(self._energy_device_le, i_row, 1, 1, 3)

        i_row += 1
        layout.addWidget(QLabel("Mono device property: "), i_row, 0, AR)
        layout.addWidget(self._energy_ppt_le, i_row, 1, 1, 3)

        i_row += 1
        layout.addWidget(QLabel("Delay range: "), i_row, 0, AR)
        layout.addWidget(self._delay_range_le, i_row, 1)
        layout.addWidget(QLabel("# of delay bins: "), i_row, 2, AR)
        layout.addWidget(self._n_delay_bins_le, i_row, 3)

        i_row += 1
        layout.addWidget(QLabel("Energy range: "), i_row, 0, AR)
        layout.addWidget(self._energy_range_le, i_row, 1)
        layout.addWidget(QLabel("# of energy bins: "), i_row, 2, AR)
        layout.addWidget(self._n_energy_bins_le, i_row, 3)

        i_row += 1
        layout.addWidget(self._reset_btn, i_row, 3)

        self.setLayout(layout)

    def initConnections(self):
        """Overload."""
        mediator = self._mediator

        self._delay_device_le.value_changed_sgn.connect(
            mediator.onTrXasDelayDeviceChange)
        self._delay_ppt_le.value_changed_sgn.connect(
            mediator.onTrXasDelayPropertyChange)

        self._energy_device_le.value_changed_sgn.connect(
            mediator.onTrXasEnergyDeviceChange)
        self._energy_ppt_le.value_changed_sgn.connect(
            mediator.onTrXasEnergyPropertyChange)

        self._n_delay_bins_le.value_changed_sgn.connect(
            mediator.onTrXasNoDelayBinsChange)
        self._delay_range_le.value_changed_sgn.connect(
            mediator.onTrXasDelayRangeChange)

        self._n_energy_bins_le.value_changed_sgn.connect(
            mediator.onTrXasNoEnergyBinsChange)
        self._energy_range_le.value_changed_sgn.connect(
            mediator.onTrXasEnergyRangeChange)

        self._reset_btn.clicked.connect(mediator.onTrXasReset)

    def updateMetaData(self):
        """Overload."""
        self._delay_device_le.returnPressed.emit()
        self._delay_ppt_le.returnPressed.emit()

        self._energy_device_le.returnPressed.emit()
        self._energy_ppt_le.returnPressed.emit()

        self._n_delay_bins_le.returnPressed.emit()
        self._delay_range_le.returnPressed.emit()

        self._n_energy_bins_le.returnPressed.emit()
        self._energy_range_le.returnPressed.emit()

        return True
