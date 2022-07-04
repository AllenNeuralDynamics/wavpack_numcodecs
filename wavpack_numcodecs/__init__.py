import numcodecs
from .wavpack import WavPackCodec, has_wavpack, get_wavpack_version, get_max_channels

# add to regisrty
numcodecs.register_codec(WavPackCodec)

from .version import version as __version__
