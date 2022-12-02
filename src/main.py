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

from calculos_siseln import getCCPRxL_CCPxCON, getPR2value, get_freq_from_PR2, get_duty_cycle_from_CCPRxL_CCPxCON

from constants import PICValues
from protocol import SerialPortStatus, SerialPort


def generate_voltage_level_boost(frequency: float,
                                 duty_cycle: float,
                                 input_voltage: float,
                                 cycles: int = 5,
                                 loss: float = 0):
    nyquist = 1 / (frequency * 2)
    sampling_period = nyquist * (1 / 1000)
    period = 1 / frequency
    samples = int(cycles * period / sampling_period)

    return [(t * sampling_period, (input_voltage / (1 - duty_cycle)) - loss) for t in range(samples)]


def generate_pwm_pulse(frequency: float,
                       duty_cycle: float,
                       amplitude: float,
                       cycles: int = 5):

    nyquist = 1 / (frequency * 2)
    sampling_period = nyquist * (1 / 1000)
    period = 1 / frequency
    samples = int(cycles * period / sampling_period)

    time = (t * sampling_period for t in range(samples))
    timeseries = []

    for t in time:
        time_since_last_period = t % period

        if duty_cycle == 0:
            voltage = 0
        elif (time_since_last_period / period) - duty_cycle < sys.float_info.epsilon:
            voltage = amplitude
        else:
            voltage = 0

        timeseries.append((t, voltage))

    return timeseries


def generate_sin(amplitude: float, frequency: float):
    t = (t * 0.001 for t in range(2000))

    return [(t, amplitude * sin(2 * pi * frequency * t)) for t in t]


class SISELNGraph(Graph):
    def __init__(self, **kwargs):
        super().__init__(
            xlabel='Tiempo (s)',
            ylabel='Voltaje (V)',

            padding=10,

            y_ticks_major=2.5,
            x_ticks_major=1,

            x_grid=True,
            y_grid=True,
            x_grid_label=True,
            y_grid_label=True,

            xmin=0,
            xmax=0.000002,
            **kwargs
        )

        # Colores
        self.background_color = [0.9, 0.9, 1, 1]
        self.tick_color = [0.3, 0.3, 0.3, .7]
        self.border_color = [0, 0, 0, .7]
        self.label_options = {'color': [0, 0, 0, 1]}
        self.border_color = [0.3, 0.3, 0.3, 1]


class VoltageOutputGraph(SISELNGraph):
    voltage_input = NumericProperty(12)
    voltage_loss = NumericProperty(2)

    frequency = BoundedNumericProperty(
        20e3,
        min=PICValues.MIN_FREQ,
        max=PICValues.MAX_FREQ
    )

    duty_cycle = BoundedNumericProperty(
        0.5,
        min=PICValues.MIN_DUTY_CYCLE - .1,
        max=PICValues.MAX_DUTY_CYCLE + .1
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ymin = 10
        self.ymax = 26

        self.plot = LinePlot(color=[1, 0, 0, 1],
                             line_width=2)

        self.plot.points = generate_voltage_level_boost(
            self.frequency,
            self.duty_cycle,
            5,
            loss=self.voltage_loss,
        )

        self.period = 1 / self.frequency

        self._redraw_trigger = Clock.create_trigger(lambda *_: self._redraw_plot())

        self.add_plot(self.plot)

    def _redraw_plot(self, init: bool = False):
        # if not init:
        #     self.remove_plot(self.plot)

        self.plot.points = generate_voltage_level_boost(
            self.frequency,
            self.duty_cycle,
            12,
            loss=self.voltage_loss,
        )

        self.x_ticks_major = 10 ** log(self.period, 10)
        self.xmax = self.period * 5

        self.plot.draw()

    def on_duty_cycle(self, *_):
        self._redraw_trigger()

    def on_frequency(self, *_):
        self.period = 1 / self.frequency

        self._redraw_trigger()


class PWMGraph(SISELNGraph):
    frequency = BoundedNumericProperty(
        20e3,
        min=PICValues.MIN_FREQ,
        max=PICValues.MAX_FREQ,
    )

    duty_cycle = BoundedNumericProperty(
        0.5,
        min=PICValues.MIN_DUTY_CYCLE - .1,
        max=PICValues.MAX_DUTY_CYCLE + .1,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ymin = -1
        self.ymax = 6

        self.plot = LinePlot(color=[1, 0, 0, 1],
                             line_width=2)
        self.add_plot(self.plot)

        self.period = 1 / self.frequency

        self._redraw_trigger = Clock.create_trigger(lambda *_: self._redraw_plot())
        self._redraw_plot(init=True)

    def _redraw_plot(self, init: bool = False):
        self.plot.points = generate_pwm_pulse(self.frequency, self.duty_cycle, 5)
        self.x_ticks_major = 10 ** log(self.period, 10)
        self.xmax = self.period * 5

        self.plot.draw()

    def on_duty_cycle(self, *_):
        self._redraw_trigger()

    def on_frequency(self, *_):
        self.period = 1 / self.frequency

        self._redraw_trigger()


class DeviceButton(Button):
    device = ObjectProperty(None)


class DCDCConverterGUI(FloatLayout):
    MAX_FREQ = NumericProperty(PICValues.MAX_FREQ)
    MIN_FREQ = NumericProperty(PICValues.MIN_FREQ)

    MAX_DUTY_CYCLE = NumericProperty(PICValues.MAX_DUTY_CYCLE)
    MIN_DUTY_CYCLE = NumericProperty(PICValues.MIN_DUTY_CYCLE)

    _pwm_duty_cycle_slider = ObjectProperty(None)
    _pwm_frequency_slider = ObjectProperty(None)

    _pwm_graph: Optional[PWMGraph] = ObjectProperty(None)
    _output_voltage_graph: Optional[PWMGraph] = ObjectProperty(None)

    _send_button = ObjectProperty(None)

    _device_selection_button = ObjectProperty(None)
    _disconnect_device_button = ObjectProperty(None)

    _status_label = ObjectProperty(None)
    _status_bar = ObjectProperty(None)

    def __init__(self):
        super().__init__()

        self._pwm_duty_cycle_slider.bind(value=self.on_duty_cycle_change)
        self._pwm_frequency_slider.bind(value=self.on_frequency_change)
        self._device_selection_button.bind(on_release=self.on_device_selection_released)
        self._disconnect_device_button.bind(on_release=self.disconnect_device)

        self.frequency = self._pwm_frequency_slider.value
        self.duty_cycle = self._pwm_duty_cycle_slider.value

        self.connected_devices = []

        Clock.schedule_interval(self.detect_connected_devices, 0.15)

        self.serial_port = SerialPort()
        self.ready = False

        Clock.schedule_interval(self.sync_device, 0.05)

    def set_bar_to_error(self, error_text: str):
        pass

    def set_bar_to_success(self, success_text: str):
        self._status_label.text = success_text
        self._status_bar.color = (.2, .6, .2)

    def sync_device(self, *_):
        if self.serial_port.status == SerialPortStatus.NOT_CONNECTED:
            self.set_bar_to_success('No conectado')

            self.ready = False
        elif self.serial_port.status == SerialPortStatus.TIMEOUT_ERROR:
            self._status_label.text = f'El dispositivo excedió el tiempo de espera.'
            self._status_bar.color = (.6, .2, .2)

            self.ready = False
        elif self.serial_port.status == SerialPortStatus.COULD_NOT_CONNECT_ERROR:
            self._status_label.text = f'No se pudo conectar al dispositivo.'
            self._status_bar.color = (.6, .2, .2)

            self.ready = False
        elif self.serial_port.status == SerialPortStatus.CONNECTED and self.ready:
            self._status_label.text = f'Conectado al dispositivo en {self.serial_port.port_name}.'
            self._status_bar.color = (.2, .6, .2)

            self.serial_port.sync(self.frequency, self.duty_cycle)

            self.ready = True
        elif self.serial_port.status == SerialPortStatus.DISCONNECTED:
            self._status_label.text = f'Desconectado.'
            self._status_bar.color = (.2, .6, .2)

            self.ready = False

    def on_duty_cycle_change(self, _, duty_cycle: float):
        """ Cuando cambia  """
        self._pwm_graph.duty_cycle = duty_cycle
        self._output_voltage_graph.duty_cycle = duty_cycle

        self.duty_cycle = duty_cycle

    def on_frequency_change(self, _, frequency: float):
        self._pwm_graph.frequency = frequency
        self._output_voltage_graph.frequency = frequency

        self.frequency = frequency

    def on_device_selection_released(self, *_):
        drop_down_menu = DropDown()
        drop_down_menu.open(self._device_selection_button)

        drop_down_menu.clear_widgets()

        # Por cada dispositivo conectado, crea un butón
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

        """ 
        Si la conexión se realiza con éxito, obtiene los valores de los registro del PIC y 
        se calculan los valores de frecuencia y duty cycle correspondientes a los valores 
        """

        self.sync_device()

        PR2, CCPRxL, CCPxCON = connection_result

        frequency = get_freq_from_PR2(PR2, PICValues.F_OSC, PICValues.TMR2_PRESCALER)
        duty_cycle = get_duty_cycle_from_CCPRxL_CCPxCON(CCPRxL, CCPxCON, PR2)

        self.set_frequency(frequency)
        self.set_duty_cycle(duty_cycle)

        self.ready = True

    def disconnect_device(self, *_):
        self.serial_port.exit()

        self._status_label.text = f'Desconectado'

        Logger.info('Dispositivo desconectado')


Builder.load_file('dcdcconvertergui.kv')


class PWMControllerApp(App):
    def build(self):
        return DCDCConverterGUI()


if __name__ == '__main__':
    PWMControllerApp().run()
