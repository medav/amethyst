import sys
import os

sys.path.append('./src')

from atlas import *
from config import config as C
import regfile


geode = Circuit(True, True)

with geode:
    top = regfile.RegisterFile()

geode.SetTop(top)
EmitCircuit(geode, 'geode.v')