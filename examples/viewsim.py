import pickle
from bdsim import BDStruct
import sys

sys.setrecursionlimit(20_000)

with open("bd.out", "rb") as f:
    out = pickle.load(f)

print(out)
