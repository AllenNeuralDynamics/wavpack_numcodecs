from pathlib import Path
from cpython.buffer cimport PyBUF_ANY_CONTIGUOUS, PyBUF_WRITEABLE
from cpython.bytes cimport PyBytes_FromStringAndSize, PyBytes_AS_STRING

import numpy as np

from numcodecs.compat_ext cimport Buffer
from numcodecs.compat_ext import Buffer
from numcodecs.compat import ensure_contiguous_ndarray
from numcodecs.abc import Codec


parent = Path(__file__).parent

cdef extern from "wavpack_local.h":
    const char* WavpackGetLibraryVersionString()

cdef extern from "encoder.c":
    size_t WavpackEncodeFile (void *source, size_t num_samples, size_t num_chans, int level, float bps, void *destin, 
                              size_t destin_bytes, int dtype)

cdef extern from "decoder.c":
    size_t WavpackDecodeFile (void *source, size_t source_bytes, int *num_chans, int *bytes_per_sample, void *destin, 
                              size_t destin_bytes)


VERSION_STRING = WavpackGetLibraryVersionString()
VERSION_STRING = str(VERSION_STRING, 'ascii')
__version__ = VERSION_STRING


dtype_enum = {
    "int8": 0,
    "int16": 1,
    "int32": 2,
    "uint8": 3,
    "uint16": 4,
    "uint32": 5,
    "float": 6
}


def compress(source, int level, int num_samples, int num_chans, float bps, int dtype):
    """Compress data.

    Parameters
    ----------
    source : bytes-like
        Data to be compressed. Can be any object supporting the buffer
        protocol.
    acceleration : int
        Acceleration level. The larger the acceleration value, the faster the algorithm, but also
        the lesser the compression.

    Returns
    -------
    dest : bytes
        Compressed data.

    Notes
    -----
    The compressed output includes a 4-byte header storing the original size of the decompressed
    data as a little-endian 32-bit integer.

    """

    cdef:
        char *source_ptr
        char *dest_ptr
        char *dest_start
        Buffer source_buffer
        int source_size, dest_size, compressed_size
        bytes dest


    # setup source buffer
    source_buffer = Buffer(source, PyBUF_ANY_CONTIGUOUS)
    source_ptr = source_buffer.ptr
    source_size = source_buffer.nbytes

    try:

        # setup destination
        dest = PyBytes_FromStringAndSize(NULL, source_size)
        dest_ptr = PyBytes_AS_STRING(dest)
        dest_size = source_size

        compressed_size = WavpackEncodeFile(source_ptr, num_samples, num_chans, level, bps, dest_ptr, dest_size, dtype)

    finally:

        # release buffers
        source_buffer.release()

    # check compression was successful
    if compressed_size == -1:
        raise RuntimeError(f'WavPAck compression error: {compressed_size}')

    # resize after compression
    dest = dest[:compressed_size]

    return dest


def decompress(source, dest=None):
    """Decompress data.

    Parameters
    ----------
    source : bytes-like
        Compressed data. Can be any object supporting the buffer protocol.
    dest : array-like, optional
        Object to decompress into.

    Returns
    -------
    dest : bytes
        Object containing decompressed data.

    """
    cdef:
        char *source_ptr
        char *source_start
        char *dest_ptr
        Buffer source_buffer
        Buffer dest_buffer = None
        int source_size, dest_size, decompressed_samples
        int num_chans
        int *num_chans_ptr = &num_chans
        int bytes_per_sample
        int *bytes_per_sample_ptr = &bytes_per_sample

    # setup source buffer
    source_buffer = Buffer(source, PyBUF_ANY_CONTIGUOUS)
    source_ptr = source_buffer.ptr
    source_size = source_buffer.nbytes

    try:

        # setup destination
        if dest is None:
            # allocate memory
            dest_size = int(source_size * 20)
            dest = PyBytes_FromStringAndSize(NULL, dest_size)
            dest_ptr = PyBytes_AS_STRING(dest)
        else:
            arr = ensure_contiguous_ndarray(dest)
            dest_buffer = Buffer(arr, PyBUF_ANY_CONTIGUOUS | PyBUF_WRITEABLE)
            dest_ptr = dest_buffer.ptr
            dest_size = dest_buffer.nbytes

        print(f"Dest size {dest_size}")
        decompressed_samples = WavpackDecodeFile(source_ptr, source_size, num_chans_ptr, bytes_per_sample_ptr, 
                                                 dest_ptr, dest_size)

    finally:

        # release buffers
        source_buffer.release()
        if dest_buffer is not None:
            dest_buffer.release()

    # check decompression was successful
    if decompressed_samples <= 0:
        raise RuntimeError(f'WavPack decompression error: {decompressed_samples}')

    print(f"Bytes per sample: {bytes_per_sample} - num chans: {num_chans} - decompressed samples: {decompressed_samples}")

    return dest[:decompressed_samples * num_chans * bytes_per_sample]


        
class WavPack(Codec):    
    codec_id = "wavpack"
    max_block_size = 131072
    supported_dtypes = ["int8", "int16", "int32", "uint8", "uint16", "uint32", "float32"]
    max_channels = 4096
    max_buffer_size = 0x7E000000

    def __init__(self, level=1, bps=None, debug=False):
        """
        Numcodecs Codec implementation for WavPack (https://www.wavpack.com/) codec.

        2D buffers exceeding the supported number of channels (buffer's second dimension) and 
        buffers > 2D are flattened before compression.


        Parameters
        ----------
        compression_mode : str, optional
            The wavpack compression mode ("default", "f", "h", "hh"), by default "default"
        bps : float or None, optional
            If the hybrid factor is given, the hybrid mode is used and compression is lossy. 
            The hybrid factor is between 2.25 and 24 (it can be a decimal, e.g. 3.5) and it 
            is the average number of bits used to encode each sample, by default None
        debug : bool
            If True, prints debug commands
        """
        self.level = int(level)
        assert self.level in (1, 2, 3, 4)
        self.debug = debug

        if bps is not None:
            if bps > 0:
                self.bps = max(bps, 2.25)
            else:
                self.bps = 0
        else:
            self.bps = 0
        
    def get_config(self):
        # override to handle encoding dtypes
        return dict(
            id=self.codec_id,
            level=self.level,
            bps=float(self.bps)
        )

    def _prepare_data(self, buf):
        # checks
        assert str(buf.dtype) in self.supported_dtypes, f"Unsupported dtype {buf.dtype}"
        if buf.ndim == 1:
            data = buf[:, None]
        elif buf.ndim == 2:
            _, nchannels = buf.shape
            
            if nchannels > self.max_channels:
                data = buf.flatten()[:, None]    
            else:
                data = buf   
        else:
            data = buf.flatten()[:, None]    
        return data

    def encode(self, buf):
        data = self._prepare_data(buf)
        dtype = str(data.dtype)
        if self.debug:
            print(f"Data shape: {data.shape}")
        nsamples, nchans = data.shape
        dtype_id = dtype_enum[dtype]
        print(dtype_id)
        return compress(data, self.level, nsamples, nchans, self.bps, dtype_id)

    def decode(self, buf, out=None):        
        buf = ensure_contiguous_ndarray(buf, self.max_buffer_size)
        return decompress(buf, out)
