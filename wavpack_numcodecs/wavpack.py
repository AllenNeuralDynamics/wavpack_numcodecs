import subprocess
import shutil
import platform

import numpy as np
from pathlib import Path
from copy import copy

from numcodecs.abc import Codec
from numcodecs.compat import ndarray_copy


lib_folder = Path(__file__).parent / "lib"


def has_wavpack():
    wvpack = shutil.which('wavpack')
    wvunpack = shutil.which('wvunpack')
    if wvpack is not None and wvunpack is not None:
        return True
    else:
        return False

# here we test if the wavpack command is present in the system. If so, we use that command by default
if has_wavpack():
    if platform.system() != "Windows":
        wavpack_lib_cmd = "wavpack"
        wvunpack_lib_cmd = "wvunpack"
    else:
        wavpack_lib_cmd = "wavpack.exe"
        wvunpack_lib_cmd = "wvunpack.exe"
else: # use pre-built libraries
    if platform.system() == "Linux":
        wavpack_lib_cmd = str((lib_folder / "linux" / "wavpack").resolve().absolute())
        wvunpack_lib_cmd = str((lib_folder / "linux" / "wvunpack").resolve().absolute())
    elif platform.system() == "Darwin":
        wavpack_lib_cmd = str((lib_folder / "macos" / "wavpack").resolve().absolute())
        wvunpack_lib_cmd = str((lib_folder / "macos" / "wvunpack").resolve().absolute())
    elif platform.system() == "Windows": # Windows
        wavpack_lib_cmd = str((lib_folder / "windows" / "wavpack.exe").resolve().absolute())
        wvunpack_lib_cmd = str((lib_folder / "windows" / "wvunpack.exe").resolve().absolute())



class WavPackCodec(Codec):    
    codec_id = "wavpack"
    max_channels = 1024
    max_block_size = 131072
    supported_dtypes = ["int8", "int16", "int32", "uint8", "uint16", "uint32", "float32"]

    def __init__(self, compression_mode="default", 
                 hybrid_factor=None, pair_unassigned=False, 
                 set_block_size=False, sample_rate=48000, 
                 dtype="int16", use_system_wavpack=False,
                 debug=False):
        """
        Numcodecs Codec implementation for WavPack (https://www.wavpack.com/) codec.

        The implementation uses the "wavpack" and "wvunpack" CLI (for encoding and decoding, respectively),
        and uses pipes to transfer input and output streams between processes. 

        2D buffers exceeding the supported number of channels (buffer's second dimension) and 
        buffers > 2D are flattened before compression.


        Parameters
        ----------
        compression_mode : str, optional
            The wavpack compression mode ("default", "f", "h", "hh"), by default "default"
        hybrid_factor : float or None, optional
            If the hybrid factor is given, the hybrid mode is used and compression is lossy. 
            The hybrid factor is between 2.25 and 24 (it can be a decimal, e.g. 3.5) and it 
            is the average number of bits used to encode each sample, by default None
        pair_unassigned : bool, optional
            Encodes unassigned channels into stereo pairs, by default False
        set_block_size : bool, optional
            If True, it tries to fit all the data in one block (max 131072), by default False
        sample_rate : int, optional
            The sample rate that wavpack internally uses, by default 48000
        dtype : str, optional
            The target data type for the compressor. Note that this needs to be specified at
            instantiation, by default "int16"
        use_system_wavpack : bool
            If True, the codec uses the system's "wavpack" and "wvunpack" commands, by default False
        debug : bool
            If True, prints debug commands

        Notes
        -----
        The binaries shipped with the package support a different maximum number of channels for 
        different OSs:
            * Linux : 1024
            * macOS : 256
            * Windows : 256
        """
        self.compression_mode = compression_mode   
        self.pair_unassigned = pair_unassigned
        self.set_block_size = set_block_size
        self.hybrid_factor = hybrid_factor
        self.sample_rate = sample_rate
        self.dtype = np.dtype(dtype)
        self.use_system_wavpack = use_system_wavpack
        self.debug = debug

        assert self.dtype.name in self.supported_dtypes

        if hybrid_factor is not None:
            self.hybrid_factor = max(hybrid_factor, 2.25)

        # prepare encode base command
        if use_system_wavpack:
            assert has_wavpack(), "'wavpack' and 'wvunpack' commands not found!"
            wavpack_cmd = "wavpack"
            wvunpack_cmd = "wvunpack"
        else:
            wavpack_cmd = wavpack_lib_cmd
            wvunpack_cmd = wvunpack_lib_cmd

        base_enc_cmd = [wavpack_cmd, "-y"]
        if self.compression_mode in ["f", "h", "hh"]:
            base_enc_cmd += [f"-{compression_mode}"]
        if self.hybrid_factor is not None:
            base_enc_cmd += [f"-b{hybrid_factor}"]
        if self.pair_unassigned:
            base_enc_cmd += ["--pair-unassigned-chans"]
        self.base_enc_cmd = base_enc_cmd

        # prepare decode base command
        self.base_dec_cmd = [wvunpack_cmd, "-y", "-q"]

    def get_config(self):
        # override to handle encoding dtypes
        return dict(
            id=self.codec_id,
            compression_mode=self.compression_mode,
            hybrid_factor=self.hybrid_factor,
            pair_unassigned=self.pair_unassigned,
            set_block_size=self.set_block_size,
            sample_rate=self.sample_rate,
            dtype=str(self.dtype),
            use_system_wavpack=self.use_system_wavpack
        )

    def _prepare_data(self, buf):
        # checks
        assert buf.dtype.kind in ["i", "u", "f"]
        assert buf.dtype == self.dtype, f"Wrong dtype initialization! The data to encode should be {self.dtype}"
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
        cmd = copy(self.base_enc_cmd)
        data = self._prepare_data(buf)
        nsamples, nchans = data.shape
        nbits = int(data.dtype.itemsize * 8)

        if self.set_block_size:
            blocksize = min(nsamples, self.max_block_size)
            cmd += [f"--blocksize={blocksize}"]
        
        if self.dtype.kind != "f":
            cmd += [f"--raw-pcm={int(self.sample_rate)},{nbits},{nchans}"]
        else:
            cmd += [f"--raw-pcm={int(self.sample_rate)},{nbits}f,{nchans}"]
        cmd += ["-q", "-", "-o", "-"] 
        
        if self.debug:
            print(" ".join(cmd))
        
        # pipe buffer to wavpack stdin and return encoded in stdout
        wavenc = subprocess.run(cmd, input=data.tobytes(), capture_output=True)
        
        if wavenc.returncode == 0:
            enc = wavenc.stdout
        else:
            raise RuntimeError(f"wavpack encode failed with error: {wavenc.stderr}")
        
        return enc

    def decode(self, buf, out=None):        
        cmd = copy(self.base_dec_cmd)

        # use pipe
        cmd += ["--raw", "-", "-o", "-"]
        
        if self.debug:
            print(" ".join(cmd))

        # pipe buffer to wavpack stdin and return decoded in stdout
        wvdec = subprocess.run(cmd, input=buf, capture_output=True)
        
        if wvdec.returncode == 0:
            dec = np.frombuffer(wvdec.stdout, dtype=self.dtype)
        else:
            raise RuntimeError(f"wavpack encode failed with error: {wvdec.stderr}")
        
        # handle output
        out = ndarray_copy(dec, out)
        
        return out
