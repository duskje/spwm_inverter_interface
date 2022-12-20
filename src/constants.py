from dataclasses import dataclass


@dataclass(frozen=True)
class PICValues:
    """ Valores de diesño """

    MIN_FREQ: float = 20e3
    MAX_FREQ: float = 30e3

    MIN_DUTY_CYCLE: float = .10
    MAX_DUTY_CYCLE: float = .57

    MIN_MODULATION_INDEX: float = 0.80
    MAX_MODULATION_INDEX: float = 0.95


    """ Valores de configureción del microcontrolador """

    F_OSC: float = 48e6
    TMR2_PRESCALER: int = 16
