from math import sin, pi

from itertools import tee

def generate_sin_table(switching_frequency: float, output_frequency:float):
    N = int(switching_frequency / output_frequency)

    sin_samples = [sin(2 * pi * k / N) for k in range(N)]

    result = "const float sin_samples [] = {\n"

    for sample in sin_samples[:-1]:
        result +=  str(sample) + ",\n"

    result += str(sin_samples[-1]) + "\n"
    result += "}"

    return result

def generate_init_duty_cycle_table(switching_frequency: float, output_frequency:float):
    N = int(switching_frequency / output_frequency)

    sin_samples = [sin(2 * pi * k / N) for k in range(N)]

    result = "const float duty_cycle_samples [] = {\n"

    for duty_cycle in get_duty_cycle_samples(switching_frequency, output_frequency, M=0.5):




def write_spwm_header_file(switching_frequency: float, output_frequency:float):
    with open("spwm_init.h", "w+") as f:
        f.write(generate_sin_table(switching_frequency, output_frequency))


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

    duty_cycle_samples = get_duty_cycle_samples(switching_frequency_hz, output_frequency_hz, 0.1)

    write_spwm_header_file(switching_frequency_hz, output_frequency_hz)
    print(duty_cycle_samples)
