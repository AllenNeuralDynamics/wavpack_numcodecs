import numcodecs
from .wavpack import WavPackCodec

# add to regisrty
numcodecs.register_codec(WavPackCodec)

from .version import version as __version__
