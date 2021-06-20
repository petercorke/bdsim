from bdsim.components import Clock
from typing import Optional, Union
from bdsim import BlockDiagram, Block, Plug, BDSim
from scipy.signal import tf2ss, TransferFunction

sim = BDSim(animation=True)
bd: BlockDiagram = sim.blockdiagram()

Signal = Union[Block, Plug]

ADC_PIN = 0
PWM_PIN = 0
GPIO_V = 3.3

FREQ = 20
# offsets chosen after observing execution
ADC_OFFSET          = 0.0
CONTROLLER_OFFSET   = 0.015 # adc + gc.collect() execution takes <= 15ms
PWM_OFFSET          = 0.027 # controller execution takes <= 12ms
DATASENDER_OFFSET   = 0.039 # execution takes <= 12ms

FREQ = 18
R = 4.7e3
L = 47e-4 # +- 5%
C = 100e-6


def vc_rlc(V_s: Signal, r: float, l: float, c: float):
    "Transfer function for voltage across a capacitor in an RLC circuit"

    A, B, C, _ = tf2ss(1, [l * c, r * c, 1])
    # full_state_feedback = np.eye()
    return bd.LTI_SS(V_s, A=A, B=B, C=C)

def discrete_pi_controller(clock: Clock, p: float, i: float, *, min: float = -float('inf'), max=float('inf')):
    "Discrete PI Controller"
    p_term = bd.GAIN(p)

    ss_pi = TransferFunction(clock.T * i, [1, -1], dt=clock.T).to_ss()
    i_term = bd.DISCRETE_LTI_SS(clock, A=ss_pi.A, B=ss_pi.B, C=ss_pi.C)

    block = bd.CLIP(
        bd.SUM('++', p_term, i_term),
        min=min, max=max
    )

    def register_err(err: Signal):
        p_term[0] = err
        i_term[0] = err

    return block, register_err



def control_rlc(reference: Signal):
    duty, register_err = discrete_pi_controller(bd.clock(FREQ, unit='Hz', offset=CONTROLLER_OFFSET), 20, 1, min=0, max=1)

    # max frequency allowable by ESP32 for smoothest output
    pwm_v = bd.PWM(bd.clock(FREQ, unit='Hz', offset=PWM_OFFSET), duty, freq=1000, v_range=(0, 3.3), pin=PWM_PIN)

    V_c = vc_rlc(pwm_v, R, L, C)

    adc = bd.ADC(bd.clock(FREQ, unit='Hz', offset=ADC_OFFSET), V_c, bit_width=12, v_range=(0, 3.6), pin=ADC_PIN)

    err = bd.SUM('+-', reference, adc)
    register_err(err)

    return duty, adc, V_c


def run_test():

    target = bd.STEP(T=0)
    # target = bd.WAVEFORM('sine')

    inp, adc, output = control_rlc(target)
    scope = bd.SCOPE(
        labels=["Reference", "PWM", "ADC Reading", "Output"]
    )
    scope[0] = target
    scope[1] = inp
    scope[2] = adc
    scope[3] = output

    bd.compile()
    sim.run(bd, T=6, block=True)


if __name__ == "__main__":
    run_test()
