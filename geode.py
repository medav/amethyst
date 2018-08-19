import sys
import os

sys.path.append('./rtl')

from atlas import *
from config import config as C
import core


geode = Circuit(True, True)

print('Elaborating...')
with geode:
    top = core.Core()

geode.SetTop(top)
print('Synthesizing...')
EmitCircuit(geode, 'geode.v')
print('Done!')