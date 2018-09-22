import json
from dataclasses import dataclass
from atlas import *

C = json.load(open('config.json', 'r'))

#
# Since this code is used for both the I+D caches, some disambiguation between
# the parameter sets is needed. The CacheConfig class holds all the relevant
# parameters specific to each cache.
#

@dataclass(unsafe_hash=True)
class CacheConfig(object):

    #
    # Parameters supplied via global config.
    #

    cache_type : str
    num_sets : int
    num_ways : int
    line_width : int

    #
    # Parameters computed from above.
    #

    set_addr_width : int = None
    way_addr_width : int = None
    line_width_bytes : int = None
    line_index_width : int = None
    untag_width : int = None
    tag_width : int = None

    def __post_init__(self):
        self.set_addr_width = Log2Ceil(self.num_sets)
        self.way_addr_width = Log2Ceil(self.num_ways)
        self.line_width_bytes = self.line_width // 8
        self.line_index_width = Log2Ceil(self.line_width_bytes)
        self.untag_width = self.set_addr_width + self.line_index_width
        self.tag_width = C['paddr-width'] - self.untag_width

    def Tag(self, addr):
        return addr(C['paddr-width'] - 1, self.untag_width)

    def Set(self, addr):
        return addr(self.untag_width - 1, self.line_index_width)

    def Index(self, addr):
        return addr(self.line_index_width - 1, 0)

    @staticmethod
    def FromCacheType(cache_type : str):
        return CacheConfig(
            cache_type=cache_type,
            num_sets=C[cache_type]['num-sets'],
            num_ways=C[cache_type]['num-ways'],
            line_width=C[cache_type]['line-width'])