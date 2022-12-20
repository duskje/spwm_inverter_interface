import sys

from typing import Iterable, Optional, List, Tuple, Any, Union

from math import pi, sin, log

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import BoundedNumericProperty, ObjectProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.lang.builder import Builder
from kivy.logger import Logger

from kivy_garden.graph import Graph, LinePlot

from serial.tools.list_ports import comports
from serial.tools.list_ports_common import ListPortInfo

from pic_formulas import getCCPRxL_CCPxCON, getPR2value, get_freq_from_PR2, get_duty_cycle_from_CCPRxL_CCPxCON

from constants import PICValues
from serial_communication import SerialPortStatus, SerialPort


class DeviceButton(Button):
    device = ObjectProperty(None)


class InverterGUI(FloatLayout):
    MAX_FREQ = NumericProperty(PICValues.MAX_FREQ)
    MIN_FREQ = NumericProperty(PICValues.MIN_FREQ)

    MAX_DUTY_CYCLE = NumericProperty(PICValues.MAX_DUTY_CYCLE)
    MIN_DUTY_CYCLE = NumericProperty(PICValues.MIN_DUTY_CYCLE)

    MIN_MODULATION_INDEX = NumericProperty(PICValues.MIN_MODULATION_INDEX)
    MAX_MODULATION_INDEX = NumericProperty(PICValues.MAX_MODULATION_INDEX)
    modulation_index = NumericProperty(.95)

    modulation_index_slider = ObjectProperty(None)

    _send_button = ObjectProperty(None)

    _device_selection_button = ObjectProperty(None)
    _disconnect_device_button = ObjectProperty(None)

    _status_label = ObjectProperty(None)
    _status_bar = ObjectProperty(None)

    def __init__(self):
        super().__init__()

        self._device_selection_button.bind(on_release=self.on_device_selection_released)
        self._disconnect_device_button.bind(on_release=self.disconnect_device)

        self.connected_devices = []

        Clock.schedule_interval(self.detect_connected_devices, 0.15)

        self.serial_port = SerialPort()
        self.ready = False

        Clock.schedule_interval(self.sync_device, 0.05)

    def set_bar_to_error(self, error_text: str):
        self._status_bar.color = (.6, .2, .2)
        self._status_label.text = error_text

    def set_bar_to_success(self, success_text: str):
        self._status_label.text = success_text
        self._status_bar.color = (.2, .6, .2)

    def sync_device(self, *_):
        if self.serial_port.status == SerialPortStatus.NOT_CONNECTED:
            self.set_bar_to_success('No conectado')

            self.ready = False
        elif self.serial_port.status == SerialPortStatus.TIMEOUT_ERROR:
            # todo: set_bar_to_error
            self.set_bar_to_error(f'El dispositivo excedió el tiempo de espera.')

            self.ready = False
        elif self.serial_port.status == SerialPortStatus.COULD_NOT_CONNECT_ERROR:
            self.set_bar_to_error(f'No se pudo conectar al dispositivo.')

            self.ready = False
        elif self.serial_port.status == SerialPortStatus.CONNECTED and self.ready:
            self.set_bar_to_success(f'Conectado al dispositivo en {self.serial_port.port_name}.')
            self.serial_port.sync(self.modulation_index)

            self.ready = True
        elif self.serial_port.status == SerialPortStatus.DISCONNECTED:
            self.set_bar_to_success(f'Desconectado.')
            self._status_bar.color = (.2, .6, .2)

            self.ready = False

    def on_duty_cycle_change(self, _, duty_cycle: float):
        """ Cuando cambia  """
        self._pwm_graph.duty_cycle = duty_cycle
        self._output_voltage_graph.duty_cycle = duty_cycle

        self.duty_cycle = duty_cycle

    def on_modulation_index(self, *_):
        print(int(self.modulation_index * 100))

    def on_frequency_change(self, _, frequency: float):
        self._pwm_graph.frequency = frequency
        self._output_voltage_graph.frequency = frequency

        self.frequency = frequency

    def on_device_selection_released(self, *_):
        drop_down_menu = DropDown()
        drop_down_menu.open(self._device_selection_button)

        drop_down_menu.clear_widgets()

        # Por cada dispositivo conectado, crea un botón
        for device in self.connected_devices:
            new_button = DeviceButton(size_hint_y=None,
                                      text=device.name,
                                      device=device)

            # Dependiendo del botón seleccionado del menú desplegable, nos llamará la función
            # que nos permite conectarnos al dispositivo asociado

            new_button.bind(on_release=lambda btn: self.connect_to_device(btn.device))

            drop_down_menu.add_widget(new_button)

    # TODO: Refactor
    def set_frequency(self, frequency: float):
        self._pwm_graph.frequency = frequency
        self._output_voltage_graph.frequency = frequency
        self._pwm_frequency_slider.value = frequency

        self.frequency = frequency

    def set_duty_cycle(self, duty_cycle: float):
        self._pwm_graph.duty_cycle = duty_cycle
        self._output_voltage_graph.duty_cycle = duty_cycle
        self._pwm_duty_cycle_slider.value = duty_cycle

        self.duty_cycle = duty_cycle

    def detect_connected_devices(self, *_):
        self.connected_devices = comports()

    def connect_to_device(self, port_info: ListPortInfo):
        """ En base al nombre de dispositivo, intentar conectarse al dispositivo... """

        # connection_result = self.serial_comm.connect(port_info)
        self._status_label.text = f'Conectando a {port_info.name}...'

        connection_result = self.serial_port.connect(port_info)

        if connection_result is None:
            return

        self.modulation_index = connection_result

        self.ready = True


    def disconnect_device(self, *_):
        self.serial_port.exit()

        self._status_label.text = f'Desconectado'

        Logger.info('Dispositivo desconectado')


Builder.load_file('inverter_gui.kv')


class PWMControllerApp(App):
    def build(self):
        return InverterGUI()


if __name__ == '__main__':
    PWMControllerApp().run()
