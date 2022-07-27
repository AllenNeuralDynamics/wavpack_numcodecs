from wavpack_cython.wavpack import WavPack
import numcodecs

numcodecs.register_codec(WavPack)
