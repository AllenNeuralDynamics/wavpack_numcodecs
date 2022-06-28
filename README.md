# WavPack - numcodecs 

[Numcodecs](https://numcodecs.readthedocs.io/en/latest/index.html) wrapper to the [WavPack](https://www.wavpack.com/index.html) audio codec.

This implementation enables one to use WavPack as a compressor in [Zarr](https://zarr.readthedocs.io/en/stable/index.html).

## Installation

Currently, only installation from source is supported:

```
git clone https://github.com/AllenNeuralDynamics/wavpack_numcodecs.git
cd wavpack_numcodecs
python setyp.py install (develop)
```

The package is shipped with pre-compiled binaries for Windows, macOS, and Linux (in the `wavpack_numcodecs/lib` folder). 
For Linux systems, it is **HIGHLY** recommended to build and install WavPack locally with:

```
git clone https://github.com/dbry/WavPack
cd WavPack
./autogen.sh
sudo make install
```

**NOTE**: the pre-compiled `linux` library is for a `Linux-5.13.0-44-generic-x86_64-with-glibc2.31` platform.

## Usage

This is a simple example on how to use the `WavPackCodec` with `zarr`:

```
import zarr
from wavpack_numcodecs import WavPackCodec

data = ... # any numpy array

# IMPORTANT: the dtype for the compressor needs to be specified at instantiation
wv_compressor = WavPackCodec(dtype=data.dtype, **kwargs)

z = zarr.array(data, compressor=wv_compressor)

data_read = z[:]
```
Available `**kwargs` can be browsed with: `WavPackCodec?`

**NOTE:** In order to reload in zarr an array saved with the `WavPackCodec`, you need to import `wavpack_numcodecs` in the script/notebook.