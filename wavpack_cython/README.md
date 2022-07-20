# WavPack - numcodecs Cython version

[Numcodecs](https://numcodecs.readthedocs.io/en/latest/index.html) wrapper to the [WavPack](https://www.wavpack.com/index.html) audio codec.

This implementation enables one to use WavPack as a compressor in [Zarr](https://zarr.readthedocs.io/en/stable/index.html).

## Installation

Currently, only installation from source is supported:

```
git clone https://github.com/AllenNeuralDynamics/wavpack_numcodecs.git
cd wavpack_numcodecs
python setyp.py build_ext -i install (develop)
```

## Usage

This is a simple example on how to use the `WavPackCodec` with `zarr`:

```
import zarr
from wavpack_cython import WavPack

data = ... # any numpy array

# IMPORTANT: the dtype for the compressor needs to be specified at instantiation
wv_compressor = WavPack(dtype=data.dtype, **kwargs)

z = zarr.array(data, compressor=wv_compressor)

data_read = z[:]
```
Available `**kwargs` can be browsed with: `WavPack?`

**NOTE:** In order to reload in zarr an array saved with the `WavPack`, you need to import `wavpack_cython` in the script/notebook.