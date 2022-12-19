from kivy.app import App

import numpy as np
from kivy.properties import ListProperty
from kivy_garden.graph import LinePlot
from scipy import signal
from itertools import tee

import sys

from main import SISELNGraph, generate_sin

def generate_triangle_wave(amplitude: float, frequency: float, cycles: int, samples_per_cycle: int):
    t = np.linspace(0, (1 / frequency) * cycles, samples_per_cycle * cycles)

    return amplitude * signal.sawtooth(2 * np.pi * frequency * t, width=0.5)

def generate_sin_wave(amplitude: float, frequency: float, cycles: int, samples_per_cycle: int):
    t = np.linspace(0, (1 / frequency * cycles, samples_per_cycle * cycles))

    return amplitude * np.sin(2 * np.pi * frequency * t)


def generate_spwm_signals(M: float, frequency: float, cycles: int, samples_per_cycle:int, cycle_offset: int = 0):
    period = 1 / frequency

    t = np.linspace(0, period * cycles, samples_per_cycle * cycles) + cycle_offset * period

    sine_wave = (M * np.sin(2 * np.pi * 50 * t))
    triangle_wave = (signal.sawtooth(2 * np.pi * frequency * t, width=0.5))
    spwm_wave = []

    intersects = []

    for t_sample, sine_sample, triangle_sample in zip(t, sine_wave, triangle_wave):
        if sine_sample > triangle_sample:
            spwm_wave.append(1)
        else:
            spwm_wave.append(0)

    return t, sine_wave, triangle_wave, spwm_wave, intersects


class SPWMGraph(SISELNGraph):
    sine_wave_points = ListProperty([])
    triangle_wave_points = ListProperty([])
    timeseries = ListProperty([])

    def __init__(self, timeseries, sine_wave_points, triangle_wave_points, **kwargs):
        super().__init__(**kwargs)

        self.timeseries = timeseries
        self.sine_wave_points = sine_wave_points
        self.triangle_wave_points = triangle_wave_points

        self.xmax = float(self.timeseries[-1])
        self.xmin = float(self.timeseries[0])

        self.ymax = 1 + .5
        self.ymin = -1 - .5

        self.sine_plot = LinePlot(color=[.8, .2, .2, .7],
                                  line_width=2)

        self.sine_plot.points = zip(self.timeseries, self.sine_wave_points)
        self.add_plot(self.sine_plot)

        self.triangle_plot = LinePlot(color=[.2, .2, .8, .7],
                                      line_width=2)

        self.triangle_plot.points = zip(self.timeseries, self.triangle_wave_points)
        self.add_plot(self.triangle_plot)

        self.x_ticks_major = 1 / 40e3
        self.x_ticks_minor = 6

        self.y_ticks_major = 0.5
        self.y_ticks_minor = 3


class PWMControllerApp(App):
    def build(self):
        t, sine_wave, triangle_wave, spwm_wave, intersects = generate_spwm_signals(0.8, 40e3, 5, 100, 0)

        return SPWMGraph(t, sine_wave, triangle_wave)


if __name__ == '__main__':
    PWMControllerApp().run()
