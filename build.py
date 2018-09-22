import sys
import os

sys.path.append('./rtl')
sys.path.append('../atlas')

from atlas import *
from amethyst import amethyst

circuit = Circuit('amethyst', True, True)

print('Elaborating...')
with Context(circuit):
    circuit.top = amethyst.Amethyst()

print('Synthesizing...')
EmitCircuit(circuit, 'build/amethyst.v')
print('Done!')