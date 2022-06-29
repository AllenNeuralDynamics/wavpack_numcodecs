import numcodecs
from .wavpack import WavPackCodec, has_wavpack, check_max_cli_channels

# check max CLI channels for available wavpack
WavPackCodec.set_max_cli_channels(check_max_cli_channels())

# add to regisrty
numcodecs.register_codec(WavPackCodec)

from .version import version as __version__
