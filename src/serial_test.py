from serial import Serial

from calculos_siseln import getCCPRxL_CCPxCON, getPR2value

from time import sleep


def xor_checksum(packet: bytearray):
    sum = 0

    for byte in packet:
        sum ^= byte

    return sum


def set_duty_cycle():
    PWM_freq = int(20e3) # Frecuencia de conmutación requerida
    F_osc = int(48e6) # Frecuencia del procesador
    TMR2_prescaler = 16 # Valor del prescaler
    PR2 = getPR2value(PWM_freq, F_osc, TMR2_prescaler)

    with Serial('COM5', 9600, timeout=1) as s:
        while(True):
            for percent in range(99):
                CCPR1L = getCCPRxL_CCPxCON(PR2, percent / 100)[0] >> 2
                s.write(CCPR1L.to_bytes(1, 'little'))
                print(s.readline())

set_duty_cycle()