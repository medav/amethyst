import sys
import os

sys.path.append('./rtl')

from atlas import *
from config import *
import amethyst
import cache


circuit = Circuit('amethyst', True, True)

print('Elaborating...')
with Context(circuit):
    # circuit.top = amethyst.Amethyst()
    circuit.top = cache.Cache(cache.CacheConfig.FromCacheType('dcache'))

print('Synthesizing...')
EmitCircuit(circuit, 'build/amethyst.v')
print('Done!')