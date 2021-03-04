from bdsim.components import ndarray as ndarray
from typing_extensions import TypedDict

class MultiRotorModel(TypedDict):
    nrotors: int
    g: float
    rho: float
    muv: float
    M: float
    J: ndarray
    h: float
    d: float
    nb: int
    r: float
    c: float
    e: float
    Mb: float
    Mc: float
    ec: float
    Ib: float
    Ic: float
    mb: float
    Ir: float
    Ct: float
    Cq: float
    sigma: float
    thetat: float
    theta0: float
    theta1: float
    theta75: float
    thetai: float
    a: float
    A: float
    gamma: float
    b: float
    k: float
    verbose: bool

def new_quadrotor_model(): ...
