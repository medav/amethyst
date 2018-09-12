import sys
import os

sys.path.append('./rtl')

from atlas import *
from config import *
import amethyst
import ifetch


circuit = Circuit('amethyst', True, True)

print('Elaborating...')
with Context(circuit):
    # circuit.top = amethyst.Amethyst()
    circuit.top = ifetch.IFetchStage()

print('Synthesizing...')
EmitCircuit(circuit, 'build/amethyst.v')
print('Done!')