import sys
import os

sys.path.append('./rtl')

from atlas import *
from config import config as C
import amethyst
import icache


circuit = Circuit('amethyst', True, True)

print('Elaborating...')
with Context(circuit):
    # circuit.top = amethyst.Amethyst()
    circuit.top = icache.ICache()

print('Synthesizing...')
EmitCircuit(circuit, 'build/amethyst.v')
print('Done!')