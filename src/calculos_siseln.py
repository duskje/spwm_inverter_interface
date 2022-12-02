from typing import Tuple, List


def getPR2value(PWM_freq: float, F_osc: float, TMR2_prescaler: int) -> float:
    """
    Obtiene el valor para el registro PR2 necesario para operar a las
    condiciones especificadas.
    """
    # Latex: \text{PR2} = \frac{F_{\text{PWM}}}{F_{\text{PWM}} \cdot 4 \cdot \text{TMR2}_{\text{Prescaler}}} - 1
    return int(F_osc / (PWM_freq * 4 * TMR2_prescaler) - 1)


def get_freq_from_PR2(PR2: int, F_osc: float, TMR2_prescaler: int) -> float:
    return F_osc / ((PR2 + 1) * 4 * TMR2_prescaler)


def possiblePR2values(F_osc: float, TMR2_prescaler: int) -> List[Tuple[int, float]]:
    return [(PR2, F_osc / ((PR2 + 1) * 4 * TMR2_prescaler)) for PR2 in range(255)]


def max_possible_PR2_value(F_osc: float, TMR2_prescaler: int) -> int:
    MAX_PR2 = 255

    return int(F_osc / ((MAX_PR2 + 1) * 4 * TMR2_prescaler))

def get_duty_cycle_from_CCPRxL_CCPxCON(CCPRxL: int, CCPxCON: int, PR2: int):
    """ Obtenemos el duty cycle a partir del contenido de los registros """
    return ((CCPRxL << 2) | ((CCPxCON >> 4) & 0b11)) / (4 * (PR2 + 1))

def getCCPRxL_CCPxCON(PR2_value, dutyCycle: float) -> Tuple[int, int]:
    """
    Obtiene el valor para los registros CCPRxL y CCPxCON necesarios para operar a las
    condiciones especificadas.
    """

    if dutyCycle > 1:
        raise ValueError('Duty cycle cannot exceed 1')

    if dutyCycle < 0:
        raise ValueError('Duty cycle cannot be negative')

    # Latex: \text{CCPRxL}|\text{CCPxCON}_{\text{5:4}} = 4 \cdot D \cdot [PR2 + 1]
    result = int((PR2_value + 1) * 4 * dutyCycle)
    CCPRxL = result >> 2
    CCPxCON = result & 0b11

    return (CCPRxL, CCPxCON)


if __name__ == "__main__":
    PWM_freq = int(20e3) # Frecuencia de conmutación requerida
    F_osc = int(48e6) # Frecuencia del procesador
    TMR2_prescaler = 16 # Prescaler del timer 2

    PR2 = getPR2value(PWM_freq, F_osc, TMR2_prescaler)
    print(f'Valor PR2: {PR2}')

    CCPRxL_CCPxCON_bits = getCCPRxL_CCPxCON(PR2, 0.0)
    print(f'Valor CCPRxL: {CCPRxL_CCPxCON_bits[0]}') # Valor a escribir en CCPRxL
    print(f'Valor CCPxCON: {CCPRxL_CCPxCON_bits[1]}') # Valor a escribir en CCPxCON


# if __name__ == '__main__':
#     PWM_freq = int(20e3) # Frecuencia de conmutación requerida
#     F_osc = int(48e6) # Frecuencia del procesador
#     TMR2_prescaler = 16 # Frecuencia del preescalador
#
#     print(max_possible_PR2_value(TMR2_prescaler=TMR2_prescaler, F_osc=F_osc))
#     print(possiblePR2values(TMR2_prescaler=TMR2_prescaler, F_osc=F_osc))
