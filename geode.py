import sys
import os

sys.path.append('./rtl')

from atlas import *
from config import config as C
import core


geode = Circuit('geode', True, True)

print('Elaborating...')
with Context(geode):
    geode.top = core.GeodeCore()

print('Synthesizing...')
EmitCircuit(geode, 'build/geode.v')
print('Done!')