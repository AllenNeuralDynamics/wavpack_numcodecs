import numpy as np
from wavpack_cython import WavPack


codec = WavPack(dtype="int16")

data = (np.random.randn(1000, 20) * 1000).astype("int16")

enc = codec.encode(data)
dec = codec.decode(enc)
data_dec = np.frombuffer(dec, dtype=codec.dtype).reshape(data.shape)

assert np.allclose(data, data_dec)