from collections import namedtuple

from kivy.app import App

import numpy as np
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy_garden.graph import LinePlot, VBar, Graph
from scipy import signal


SPWMSignals = namedtuple('SPWMSignals',
                         ['t',
                          't_limits',
                          'sine_wave',
                          'triangle_wave',
                          'spwm_wave',
                          'spwm_complimentary_wave',
                          'intersects'])


def generate_spwm_signals(M: float, frequency: float, cycles: int, samples_per_cycle: int, cycle_offset: int = 0):
    period = 1 / frequency

    t = np.linspace(0, period * cycles, samples_per_cycle * cycles) + cycle_offset * period

    sine_wave = (M * np.sin(2 * np.pi * 50 * t))
    triangle_wave = (signal.sawtooth(2 * np.pi * frequency * t, width=0.5))

    indexes = np.argwhere(np.diff(np.sign(sine_wave - triangle_wave))).flatten()
    intersects = [t[index] for index in indexes]

    spwm_wave = []
    spwm_complimentary_wave = []

    for sine_sample, triangle_sample in zip(sine_wave, triangle_wave):
        if sine_sample > triangle_sample:
            spwm_wave.append(1)
            spwm_complimentary_wave.append(0)
        else:
            spwm_wave.append(0)
            spwm_complimentary_wave.append(1)

    t_start = t[0]
    t_end = t[-1]

    return SPWMSignals(t,
                       (t_start, t_end),
                       sine_wave,
                       triangle_wave,
                       spwm_wave,
                       spwm_complimentary_wave,
                       intersects)


class SISELNGraph(Graph):
    def __init__(self, **kwargs):
        super().__init__(
            padding=20,
            x_grid=True,
            y_grid=True,
            x_grid_label=True,
            y_grid_label=True,

            xmin=0,
            xmax=0.000002,
            **kwargs
        )

        # Colores
        self.background_color = [0.9, 0.9, 1, 0]
        self.tick_color = [0.3, 0.3, 0.3, .7]
        self.border_color = [0, 0, 0, .7]
        self.label_options = {'color': [0, 0, 0, 1]}
        self.border_color = [0.3, 0.3, 0.3, 1]


class ComparatorGraph(SISELNGraph):
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
                                  line_width=1.5)
        self.sine_wave_points = sine_wave_points
        self.add_plot(self.sine_plot)

        self.triangle_plot = LinePlot(color=[.2, .2, .8, .7],
                                      line_width=1.5)
        self.triangle_wave_points = triangle_wave_points
        self.add_plot(self.triangle_plot)

        self.intersects_plot = VBar(color=[.2, .8, .2, .7])
        self.intersects = intersects
        self.add_plot(self.intersects_plot)

        self.x_ticks_major = 1 / 40e3
        self.x_ticks_minor = 6

        self.y_ticks_major = 0.5
        self.y_ticks_minor = 1

    def on_intersects(self, *_):
        self.intersects_plot.points = self.intersects

    def on_sine_wave_points(self, *_):
        self.sine_plot.points = self.sine_wave_points

    def on_triangle_wave_points(self, *_):
        self.triangle_plot.points = self.triangle_wave_points

    def on_t_limits(self, *_):
        self.xmax = float(self.t_limits[0])
        self.xmin = float(self.t_limits[1])


class SPWMGraph(SISELNGraph):
    spwm_wave_points = ListProperty([])
    intersects = ListProperty([])
    t_limits = ListProperty([])

    def __init__(self, t_limits, spwm_wave_points, intersects, **kwargs):
        super().__init__(**kwargs)

        self.t_limits = t_limits

        self.ymax = 1 + .5
        self.ymin = -.5

        self.spwm_wave_plot = LinePlot(color=[.1, .1, .1, .7],
                                  line_width=1.5)

        self.spwm_wave_points = spwm_wave_points

        self.add_plot(self.spwm_wave_plot)

        self.intersects_plot = VBar(color=[.2, .8, .2, .7])

        self.intersects = intersects

        self.add_plot(self.intersects_plot)

        self.x_ticks_major = 1 / 40e3
        self.x_ticks_minor = 3

        self.y_ticks_major = 0.5
        self.y_ticks_minor = 3

    def on_intersects(self, *_):
        self.intersects_plot.points = self.intersects

    def on_spwm_wave_points(self, *_):
        self.spwm_wave_plot.points = self.spwm_wave_points

    def on_t_limits(self, *_):
        self.xmax = float(self.t_limits[0])
        self.xmin = float(self.t_limits[1])


class SPWMGraphWidget(BoxLayout):
    modulation_index = NumericProperty(.95)
    current_cycle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = 'vertical'

        spwm_signals: SPWMSignals = generate_spwm_signals(self.modulation_index,
                                                          40e3,
                                                          5,
                                                          100,
                                                          0)

        self.comparator_graph = ComparatorGraph(spwm_signals.t_limits,
                                                zip(spwm_signals.t, spwm_signals.sine_wave),
                                                zip(spwm_signals.t, spwm_signals.triangle_wave),
                                                spwm_signals.intersects)
        self.add_widget(self.comparator_graph)

        self.spwm_graph = SPWMGraph(spwm_signals.t_limits,
                                    zip(spwm_signals.t, spwm_signals.spwm_wave),
                                    spwm_signals.intersects)
        self.add_widget(self.spwm_graph)

        self.spwm_complimentary_graph = SPWMGraph(spwm_signals.t_limits,
                                                  zip(spwm_signals.t, spwm_signals.spwm_complimentary_wave),
                                                  spwm_signals.intersects)
        self.add_widget(self.spwm_complimentary_graph)

        Clock.schedule_interval(self.update_window, 0.05)

    def on_modulation_index(self, *_):
        print('modulation_index', self.modulation_index)

    def update_window(self, *_):
        self.current_cycle += 30

        spwm_signals = generate_spwm_signals(self.modulation_index,
                                             40e3,
                                             5,
                                             100,
                                             self.current_cycle)

        self.comparator_graph.t_limits = spwm_signals.t_limits
        self.comparator_graph.sine_wave_points = zip(spwm_signals.t, spwm_signals.sine_wave)
        self.comparator_graph.triangle_wave_points = zip(spwm_signals.t, spwm_signals.triangle_wave)
        self.comparator_graph.intersects = spwm_signals.intersects

        self.spwm_graph.t_limits = spwm_signals.t_limits
        self.spwm_graph.spwm_wave_points = zip(spwm_signals.t, spwm_signals.spwm_wave)
        self.spwm_graph.intersects = spwm_signals.intersects

        self.spwm_complimentary_graph.t_limits = spwm_signals.t_limits
        self.spwm_complimentary_graph.spwm_wave_points = zip(spwm_signals.t, spwm_signals.spwm_complimentary_wave)
        self.spwm_complimentary_graph.intersects = spwm_signals.intersects


class PWMControllerApp(App):
    def build(self):
        return SPWMGraphWidget()


if __name__ == '__main__':
    PWMControllerApp().run()
