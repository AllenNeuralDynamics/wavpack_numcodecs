import numcodecs
from .wavpack import WavPackCodec, has_wavpack

# add to regisrty
numcodecs.register_codec(WavPackCodec)

from .version import version as __version__
