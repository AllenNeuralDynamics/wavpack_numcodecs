from wavpack_numcodecs import WavPackCodec
import numpy as np
import zarr


def run_all_options(data):
    dtype = data.dtype
    for cmode in ["default", "f", "h", "hh"]:
        for cc in [False, True]:
            for pair in [False, True]:
                for sb in [False, True]:
                    for hf in [None, 5, 3]:
                        cod = WavPackCodec(compression_mode=cmode, cc=cc, hybrid_factor=hf,
                                           pair_unassigned=pair, set_block_size=sb,
                                           dtype=dtype)
                        enc = cod.encode(data)
                        dec = cod.decode(enc)

                        # this might not hold for pure random
                        assert len(enc) < len(dec)

                        # lossiness
                        if hf is None:
                            assert np.all(dec.reshape(data.shape) == data)


def make_noisy_sin_signals(shape=(30000, ), sin_f=100, sin_amp=100, noise_amp=10,
                           sample_rate=30000, dtype="int16"):
    assert isinstance(shape, tuple)
    assert len(shape) <= 3
    if len(shape) == 1:
        y = np.sin(2 * np.pi * sin_f * np.arange(shape[0]) / sample_rate) * sin_amp
        y = y + np.random.randn(shape[0]) * noise_amp
        y = y.astype(dtype)
    elif len(shape) == 2:
        nsamples, nchannels = shape
        y = np.zeros(shape, dtype=dtype)
        for ch in range(nchannels):
            y[:, ch] = make_noisy_sin_signals((nsamples,), sin_f, sin_amp, noise_amp,
                                              sample_rate, dtype)
    else:
        nsamples, nchannels1, nchannels2 = shape
        y = np.zeros(shape, dtype=dtype)
        for ch1 in range(nchannels1):
            for ch2 in range(nchannels2):
                y[:, ch1, ch2] = make_noisy_sin_signals((nsamples,), sin_f, sin_amp, noise_amp,
                                                        sample_rate, dtype)
    return y


def test_wavpack():
    # create test signals
    dtype = "int16"
    test1d = make_noisy_sin_signals(shape=(30000,))
    test1d_long = make_noisy_sin_signals(shape=(200000,))
    test2d = make_noisy_sin_signals(shape=(30000, 100))
    test2d_long = make_noisy_sin_signals(shape=(200000, 100))
    test2d_extra = make_noisy_sin_signals(shape=(30000, 2000))
    test3d = make_noisy_sin_signals(shape=(1000, 10, 10))

    for test_sig in [test1d, test1d_long, test2d, test2d_long, test2d_extra, test3d]:
        test_sig = test_sig.astype(dtype)


def test_zarr():
    dtype = "int16"
    test1d = make_noisy_sin_signals(shape=(30000,))
    test1d_long = make_noisy_sin_signals(shape=(200000,))
    test2d = make_noisy_sin_signals(shape=(30000, 100))
    test2d_long = make_noisy_sin_signals(shape=(200000, 100))
    test2d_extra = make_noisy_sin_signals(shape=(30000, 2000))
    test3d = make_noisy_sin_signals(shape=(1000, 10, 10))

    compressor = WavPackCodec(dtype=dtype)

    for test_sig in [test1d, test1d_long, test2d, test2d_long, test2d_extra, test3d]:
        print(test_sig.shape)
        if test_sig.ndim == 1:
            z = zarr.array(test_sig, chunks=None, compressor=compressor)
            assert z[:100].shape == test_sig[:100].shape
            assert z.nbytes_stored < z.nbytes

            z = zarr.array(test_sig, chunks=(1000), compressor=compressor)
            assert z[:100].shape == test_sig[:100].shape
            assert z.nbytes_stored < z.nbytes
        elif test_sig.ndim == 2:
            z = zarr.array(test_sig, chunks=None, compressor=compressor)
            assert z[:100, :10].shape == test_sig[:100, :10].shape
            assert z.nbytes_stored < z.nbytes

            z = zarr.array(test_sig, chunks=(1000, None), compressor=compressor)
            assert z[:100, :10].shape == test_sig[:100, :10].shape
            assert z.nbytes_stored < z.nbytes

            z = zarr.array(test_sig, chunks=(None, 10), compressor=compressor)
            assert z[:100, :10].shape == test_sig[:100, :10].shape
            assert z.nbytes_stored < z.nbytes
        else: # 3d
            z = zarr.array(test_sig, chunks=None, compressor=compressor)
            assert z[:100, :2, :2].shape == test_sig[:100, :2, :2].shape
            assert z.nbytes_stored < z.nbytes

            z = zarr.array(test_sig, chunks=(1000, 2, None), compressor=compressor)
            assert z[:100, :2, :2].shape == test_sig[:100, :2, :2].shape
            assert z.nbytes_stored < z.nbytes

            z = zarr.array(test_sig, chunks=(None, 2, 3), compressor=compressor)
            assert z[:100, :2, :2].shape == test_sig[:100, :2, :2].shape
            assert z.nbytes_stored < z.nbytes


if __name__ == '__main__':
    test_wavpack()
    test_zarr()