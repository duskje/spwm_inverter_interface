def max_switch_current(D: float, V_in_min: float, efficiency: float, V_out: float):
    return 1 - (V_in_min * efficiency) / V_out


def inductor(V_in: float,
             V_out: float,
             ripple: float,
             switching_freq: float,
             I_out_max: float):

    inductor_current_ripple = ripple * I_out_max * V_out / V_in

    return V_in * (V_out - V_in) / (inductor_current_ripple * switching_freq * V_out)


W_nominal = 10
V_nominal = 24
I_nominal = W_nominal / V_nominal

print(inductor(12, V_nominal, 0.1, 20e3, I_nominal))