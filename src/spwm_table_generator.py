from math import sin, pi

from itertools import tee
from dataclasses import dataclass
from typing import Iterable

from pic_formulas import getPR2value, getCCPRxL_CCPxCON

from pathlib import Path

MPLAB_PROJECT_PATH = Path('C:\\Users\\duskje\\MPLABXProjects\\Prototipo-Inversor.X')

@dataclass(frozen=True)
class PicPwmConfig:
    switching_frequency_hz: int # F_PWM in the datasheet
    oscillator_frequency: int # F_osc in the datasheet
    TMR2_prescaler: int


def generate_program_memory_table(type: str, variable_name: str, data: Iterable):
    data = list(data)

    result = f"const {type} {variable_name} [] = {{\n"

    for datum in data[:-1]:
        result += str(datum) + ",\n"

    result += str(data[-1]) + "\n"
    result += "};\n\n"

    return result


def generate_sin_table(switching_frequency: float, output_frequency:float):
    N = int(switching_frequency / output_frequency)

    sin_samples = [sin(2 * pi * k / N) for k in range(N)]

    return generate_program_memory_table('float', 'sin_samples', sin_samples)


def generate_init_duty_cycle_table(switching_frequency: float, output_frequency: float):
    result = "const float duty_cycle_samples_on_init [] = {\n"

    duty_cycle_samples = get_duty_cycle_samples(switching_frequency, output_frequency, M=0.5)

    for duty_cycle in duty_cycle_samples[:-1]:
        result += str(duty_cycle) + ",\n"

    result += str(duty_cycle_samples[-1]) + "\n"
    result += "};\n\n"

    return result


def generate_CCPRxL_CCPxCON(
        F_osc: int, switching_frequency: float,
        output_frequency: 50,
        modulation_index: float
):
    TMR2_prescaler = 1

    PR2 = getPR2value(switching_frequency, F_osc, TMR2_prescaler)

    duty_cycle_samples = get_duty_cycle_samples(switching_frequency_hz, output_frequency, modulation_index)

    iter1, iter2 = tee(getCCPRxL_CCPxCON(PR2, duty_cycle_sample) for duty_cycle_sample in duty_cycle_samples)

    CCPRxL_values = [CCPRxL_CCPxCON[0] for CCPRxL_CCPxCON in iter1]
    CCPxCON_values = [CCPRxL_CCPxCON[1] for CCPRxL_CCPxCON in iter2]

    result = ""
    result += generate_program_memory_table('uint8_t', f'ccprxl_values_for_{100 * modulation_index:.0f}', CCPRxL_values)
    result += generate_program_memory_table('uint8_t', f'ccpxcon_values_for_{100 * modulation_index:.0f}', CCPxCON_values)

    return result


def write_spwm_header_file(switching_frequency: float, output_frequency: float, modulation_index: float):
    with open(MPLAB_PROJECT_PATH.joinpath("spwm_tables.h"), "w+") as f:
        N = int(switching_frequency / output_frequency)  # Number of samples

        f.write('#ifndef SPWM_TABLE_H\n')
        f.write('#define SPWM_TABLE_H\n\n')
        f.write('#include <stdint.h>\n\n')
        f.write(f'#define SPWM_TABLE_SIZE {N}\n\n')
        # f.write(generate_sin_table(switching_frequency, output_frequency))
        for mod in range(80, 96):
            f.write(generate_CCPRxL_CCPxCON(int(32e6), switching_frequency, output_frequency, mod / 100))

        f.write("const uint8_t *ccprxl_tables[16] = {\n")

        for mod in range(80, 95):
            f.write(f'ccprxl_values_for_{mod},\n')

        f.write('ccprxl_values_for_95\n};\n\n')

        f.write("const uint8_t *ccpxcon_tables[16] = {\n")

        for mod in range(80, 95):
            f.write(f'ccpxcon_values_for_{mod},\n')

        f.write('ccpxcon_values_for_95\n};\n\n')

        f.write('typedef enum modulation_index_tables {\n')

        for i, mod in enumerate(range(80, 95)):
            f.write(f'MODULATION_INDEX_{mod} = {i},\n')

        f.write('MODULATION_INDEX_95 = 15\n} modulation_index_tables_enum;\n\n')

        f.write('#endif')


def get_duty_cycle_samples(switching_frequency: float, output_frequency:float, M: float):
    N = int(switching_frequency / output_frequency) # Number of samples

    switching_period = 1 / switching_frequency

    sin_samples = [sin(2 * pi * k / N) for k in range(N)]

    duty_cycle_samples = []

    for k in range(N):
        if (k + 1) >= len(sin_samples):
            break

        t_on1 = (switching_period / 4) * (1 + M * sin_samples[k])
        t_on2 = (switching_period / 4) * (1 + M * sin_samples[k + 1])

        t_on = t_on1 + t_on2

        duty_cycle_samples += [t_on / switching_period]

    return duty_cycle_samples


if __name__ == "__main__":
    switching_frequency_hz = 40e3
    output_frequency_hz = 50

    # duty_cycle_samples = get_duty_cycle_samples(switching_frequency_hz, output_frequency_hz, 0.1)
    # print(duty_cycle_samples)
    write_spwm_header_file(switching_frequency_hz, output_frequency_hz, 0.95)

