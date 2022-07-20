import numpy as np
import sys
import matplotlib.pyplot as plt

plt.ion()
plt.show()

sys.path.append("../tests")

from test_wavpackcodec import make_noisy_sin_signals, generate_test_signals
from wavpack_cython import WavPack

dtypes = ["int16", "int32"] #"uint16", "int32", "uint32", "float32"]

codec = WavPack()

for dtype in dtypes:
    print(dtype)
    data = make_noisy_sin_signals(shape=(1000, 20), dtype=dtype)
    # data = (np.random.randn(1000, 20) * 1000).astype("int16")

    enc = codec.encode(data)
    print(len(data.flatten()) * np.dtype(dtype).itemsize, len(enc))
    dec = codec.decode(enc)
    print(len(dec))
    data_dec = np.frombuffer(dec, dtype=dtype).reshape(data.shape)

    assert np.allclose(data, data_dec)