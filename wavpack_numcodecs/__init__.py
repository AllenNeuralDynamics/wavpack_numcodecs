import numcodecs
from .wavpack import WavPackPipesCodec

# add to regisrty
numcodecs.register_codec(WavPackPipesCodec)

from .version import version as __version__
