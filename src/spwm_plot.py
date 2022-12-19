from kivy.app import App

import numpy as np
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy_garden.graph import LinePlot, VBar
from scipy import signal

from itertools import tee

from main import SISELNGraph


def generate_spwm_signals(M: float, frequency: float, cycles: int, samples_per_cycle:int, cycle_offset: int = 0):
    period = 1 / frequency

    t = np.linspace(0, period * cycles, samples_per_cycle * cycles) + cycle_offset * period

    sine_wave = (M * np.sin(2 * np.pi * 50 * t))
    triangle_wave = (signal.sawtooth(2 * np.pi * frequency * t, width=0.5))

    indexes = np.argwhere(np.diff(np.sign(sine_wave - triangle_wave))).flatten()
    intersects = [t[index] for index in indexes]

    spwm_wave = []

    for sine_sample, triangle_sample in zip(sine_wave, triangle_wave):
        if sine_sample > triangle_sample:
            spwm_wave.append(1)
        else:
            spwm_wave.append(0)

    t_start = t[0]
    t_end = t[-1]

    return t, (t_start, t_end), sine_wave, triangle_wave, spwm_wave, intersects


class SPWMGraphTop(SISELNGraph):
    sine_wave_points = ListProperty([])
    triangle_wave_points = ListProperty([])
    t_limits = ListProperty([])
    intersects = ListProperty([])

    def __init__(
            self,
            t_limits,
            sine_wave_points,
            triangle_wave_points,
            intersects,
            **kwargs
    ):
        super().__init__(**kwargs)

        self.t_limits = t_limits

        self.ymax = 1 + .5
        self.ymin = -1 - .5

        self.sine_plot = LinePlot(color=[.8, .2, .2, .7],
                                  line_width=2)
        self.sine_wave_points = sine_wave_points
        self.add_plot(self.sine_plot)

        self.triangle_plot = LinePlot(color=[.2, .2, .8, .7],
                                      line_width=2)
        self.triangle_wave_points = triangle_wave_points
        self.add_plot(self.triangle_plot)

        self.intersects_plot = VBar(color=[.2, .8, .2, .7])
        self.intersects = intersects
        self.add_plot(self.intersects_plot)

        self.x_ticks_major = 1 / 40e3
        self.x_ticks_minor = 6

        self.y_ticks_major = 0.5
        self.y_ticks_minor = 3

    def on_intersects(self, *_):
        self.intersects_plot.points = self.intersects
        self.intersects_plot.draw()

    def on_sine_wave_points(self, *_):
        sine_wave_points, points_clone = tee(self.sine_wave_points)

        timeseries = [t for t, _ in points_clone]

        self.xmax = float(timeseries[-1])
        self.xmin = float(timeseries[0])

        self.sine_plot.points = self.sine_wave_points
        self.sine_plot.draw()

    def on_triangle_wave_points(self, *_):
        self.triangle_plot.points = self.triangle_wave_points
        self.triangle_plot.draw()

    def on_t_limits(self, *_):
        self.xmax = float(self.t_limits[0])
        self.xmin = float(self.t_limits[1])



class SPWMGraphBottom(SISELNGraph):
    spwm_wave_points = ListProperty([])
    intersects = ListProperty([])
    t_limits = ListProperty([])

    def __init__(self, t_limits, spwm_wave_points, intersects, **kwargs):
        super().__init__(**kwargs)

        self.t_limits = t_limits

        self.ymax = 1 + .5
        self.ymin = -.5

        self.spwm_wave_plot = LinePlot(color=[.1, .1, .1, .7],
                                  line_width=2)

        self.spwm_wave_points = spwm_wave_points

        self.add_plot(self.spwm_wave_plot)

        self.intersects_plot = VBar(color=[.2, .8, .2, .7])

        self.intersects = intersects

        self.add_plot(self.intersects_plot)

        self.x_ticks_major = 1 / 40e3
        self.x_ticks_minor = 6

        self.y_ticks_major = 0.5
        self.y_ticks_minor = 3

    def on_intersects(self, *_):
        self.intersects_plot.points = self.intersects
        self.intersects_plot.draw()

    def on_spwm_wave_points(self, *_):
        sine_wave_points, points_clone = tee(self.spwm_wave_points)

        timeseries = [t for t, _ in points_clone]

        self.xmax = float(timeseries[-1])
        self.xmin = float(timeseries[0])

        self.spwm_wave_plot.points = self.spwm_wave_points
        self.spwm_wave_plot.draw()

    def on_t_limits(self, *_):
        self.xmax = float(self.t_limits[0])
        self.xmin = float(self.t_limits[1])


class SPWMGraphWidget(BoxLayout):
    modulation_index = NumericProperty(.95)
    current_cycle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = 'vertical'

        t, t_limits, sine_wave, triangle_wave, spwm_wave, intersects = generate_spwm_signals(
            self.modulation_index, 40e3, 4, 300, 0
        )
        self.top_graph = SPWMGraphTop(t_limits, zip(t, sine_wave), zip(t, triangle_wave), intersects)
        self.add_widget(self.top_graph)
        self.bottom_graph = SPWMGraphBottom(t_limits, zip(t, spwm_wave), intersects)
        self.add_widget(self.bottom_graph)

        Clock.schedule_interval(self.update_window, 0.5)

    def update_window(self, *_):
        self.current_cycle += 5

        t, t_limits, sine_wave, triangle_wave, spwm_wave, intersects = generate_spwm_signals(
            self.modulation_index, 40e3, 4, 300, self.current_cycle
        )

        self.top_graph.sine_wave_points = zip(t, sine_wave)
        self.top_graph.triangle_wave_points = zip(t, triangle_wave)
        self.top_graph.intersects = intersects
        self.top_graph.t_limits = t_limits

        self.bottom_graph.spwm_wave_points = zip(t, spwm_wave)
        self.bottom_graph.intersects = intersects
        self.bottom_graph.t_limits = t_limits


class PWMControllerApp(App):
    def build(self):
        return SPWMGraphWidget()

if __name__ == '__main__':
    PWMControllerApp().run()
