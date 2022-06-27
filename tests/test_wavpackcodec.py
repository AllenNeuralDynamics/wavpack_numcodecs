from wavpack_numcodecs import WavPackPipesCodec
import numpy as np


def run_all_options(data):
    dtype = data.dtype
    for cmode in ["default", "f", "h", "hh"]:
        for cc in [False, True]:
            for pair in [False, True]:
                for sb in [False, True]:
                    for hf in [None, 5, 3]:
                        cod = WavPackPipesCodec(compression_mode=cmode, cc=cc, hybrid_factor=hf,
                                                pair_unassigned=pair, set_block_size=sb,
                                                dtype=dtype)
                        enc = cod.encode(data)
                        dec = cod.decode(enc)

                        # this might not hold for pure random
                        # assert len(enc) < len(dec)

                        # lossiness
                        if hf is None:
                            assert np.all(dec.reshape(data.shape) == data)


def make_correlated_signals():
    pass


def test_wavpack():
    # create test signals
    amp = 1000
    dtype = "int16"
    test1d = np.random.randn(30000) * amp
    test1d_long = np.random.randn(200000) * amp
    test2d = np.random.randn(30000, 100) * amp
    test2d_long = np.random.randn(200000, 100) * amp
    test2d_extra = np.random.randn(30000, 2000) * amp
    test3d = np.random.randn(1000, 100, 100) * amp

    for test_sig in [test1d, test1d_long, test2d, test2d_long, test2d_extra, test3d]:
        test_sig = test_sig.astype(dtype)


def test_zarr():
    pass