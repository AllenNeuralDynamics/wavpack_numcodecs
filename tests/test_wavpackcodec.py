from wavpack_numcodecs import WavPackCodec
import numpy as np
import zarr
import pytest

DEBUG = False

dtypes = ["int16", "int32", "uint16", "uint32", "float32"]

def run_all_options(data):
    dtype = data.dtype
    for cmode in ["default", "f", "h", "hh"]:
        for pair in [False, True]:
            for sb in [False, True]:
                for hf in [None, 6, 4, 2]:
                    cod = WavPackCodec(compression_mode=cmode, pair_unassigned=pair, 
                                       hybrid_factor=hf, set_block_size=sb, dtype=dtype,
                                       debug=DEBUG)
                    enc = cod.encode(data)
                    dec = cod.decode(enc)

                    if np.dtype(dtype).kind != "f":
                        assert len(enc) < len(dec)

                    # lossless
                    if hf is None:
                        assert np.all(dec.reshape(data.shape) == data)
                    # no else since if hybrid factor is high, hybrid mode could be lossless


def make_noisy_sin_signals(shape=(30000,), sin_f=100, sin_amp=100, noise_amp=10,
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


def generate_test_signals(dtype):
    test1d = make_noisy_sin_signals(shape=(3000,), dtype=dtype)
    test1d_long = make_noisy_sin_signals(shape=(200000,), dtype=dtype)
    test2d = make_noisy_sin_signals(shape=(3000, 10), dtype=dtype)
    test2d_long = make_noisy_sin_signals(shape=(200000, 4), dtype=dtype)
    test2d_extra = make_noisy_sin_signals(shape=(3000, 300), dtype=dtype)
    test3d = make_noisy_sin_signals(shape=(1000, 5, 5), dtype=dtype)

    return [test1d, test1d_long, test2d, test2d_long, test2d_extra, test3d]

@pytest.mark.numcodecs
def test_wavpack_numcodecs():
    for dtype in dtypes:
        print(f"\n\nNUMCODECS: testing dtype {dtype}\n\n")

        test_signals = generate_test_signals(dtype)

        for test_sig in test_signals:
            print(f"\tsignal shape: {test_sig.shape}")
            run_all_options(test_sig)

@pytest.mark.zarr
def test_wavpack_zarr():
    for dtype in dtypes:
        print(f"\n\nZARR: testing dtype {dtype}\n\n")
        test_signals = generate_test_signals(dtype)

        compressor = WavPackCodec(dtype=dtype, debug=DEBUG)

        for test_sig in test_signals:
            print(f"\tsignal shape: {test_sig.shape}")
            if test_sig.ndim == 1:
                z = zarr.array(test_sig, chunks=None, compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100].shape == test_sig[:100].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes

                z = zarr.array(test_sig, chunks=(1000), compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100].shape == test_sig[:100].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes
            elif test_sig.ndim == 2:
                z = zarr.array(test_sig, chunks=None, compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100, :10].shape == test_sig[:100, :10].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes

                z = zarr.array(test_sig, chunks=(1000, None), compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100, :10].shape == test_sig[:100, :10].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes

                z = zarr.array(test_sig, chunks=(None, 10), compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100, :10].shape == test_sig[:100, :10].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes
            else: # 3d
                z = zarr.array(test_sig, chunks=None, compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100, :2, :2].shape == test_sig[:100, :2, :2].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes

                z = zarr.array(test_sig, chunks=(1000, 2, None), compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100, :2, :2].shape == test_sig[:100, :2, :2].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes

                z = zarr.array(test_sig, chunks=(None, 2, 3), compressor=compressor)
                assert z[:].shape == test_sig.shape
                assert z[:100, :2, :2].shape == test_sig[:100, :2, :2].shape
                if np.dtype(dtype).kind != "f":
                    assert z.nbytes_stored < z.nbytes


if __name__ == '__main__':
    test_wavpack_numcodecs()
    test_wavpack_zarr()
