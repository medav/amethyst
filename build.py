import sys
import os

sys.path.append('./rtl')

from atlas import *
from config import config as C
import amethyst
import btb


circuit = Circuit('amethyst', True, True)

print('Elaborating...')
with Context(circuit):
    # circuit.top = amethyst.Amethyst()
    circuit.top = btb.BranchTargetBuffer()

print('Synthesizing...')
EmitCircuit(circuit, 'build/amethyst.v')
print('Done!')