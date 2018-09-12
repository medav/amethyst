import json

C = json.load(open('config.json', 'r'))

#
# Place common config options in variables
#

paddr_width = C['paddr-width']
core_width = core_width

#
# Check constraints on common options
#

assert paddr_width < core_width
assert core_width % 8 == 0