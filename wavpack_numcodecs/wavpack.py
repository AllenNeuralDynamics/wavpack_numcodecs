import subprocess
import shutil
import platform

import numpy as np
from pathlib import Path
from copy import copy

from packaging.version import parse

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
        

def get_wavpack_version():
    wvver = subprocess.run([wavpack_lib_cmd, "--version"], capture_output=True)
    wv_version = wvver.stdout.decode().split("\n")[0][len("wavpack")+1:]
    return parse(wv_version)

def get_max_channels():
    wavpack_version = get_wavpack_version()
    if wavpack_version >= parse("5.5.0"):
        return 1024
    else:
        return 256
    

class WavPackCodec(Codec):    
    codec_id = "wavpack"
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
        different wavpack versions:
            * wavpack < 5.5.0: max channels 256
            * wavpack >= 5.5.0: max channels 1024 (via --raw-pcm-ex command)
        """
        self.compression_mode = compression_mode   
        self.pair_unassigned = pair_unassigned
        self.set_block_size = set_block_size
        self.hybrid_factor = hybrid_factor
        self.sample_rate = sample_rate
        self.dtype = np.dtype(dtype)
        self.use_system_wavpack = use_system_wavpack
        self.debug = debug
        
        wavpack_version = get_wavpack_version()
        if wavpack_version >= parse("5.5.0"):
            self.max_channels = 1024
            self.pack_cmd = "--raw-pcm-ex"
        else:
            self.max_channels = 256
            self.pack_cmd = "--raw-pcm"

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
        
    @staticmethod
    def get_max_cli_channels():
        return get_max_channels()

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
        dtype = data.dtype
        if self.debug:
            print(f"Data shape: {data.shape}")
        nsamples, nchans = data.shape
        nbits = int(dtype.itemsize * 8)

        if self.set_block_size:
            blocksize = min(nsamples, self.max_block_size)
            cmd += [f"--blocksize={blocksize}"]
        
        if dtype.kind != "f":
            cmd += [f"{self.pack_cmd}={int(self.sample_rate)},{nbits},{nchans}"]
        else:
            cmd += [f"{self.pack_cmd}={int(self.sample_rate)},{nbits}f,{nchans}"]
        cmd += ["-q", "-", "-o", "-"] 
        
        if self.debug:
            print(" ".join(cmd), flush=True)
        
        # pipe buffer to wavpack stdin and return encoded in stdout
        wavenc = subprocess.run(cmd, input=data.tobytes(), capture_output=True)
        enc = wavenc.stdout
        
        if wavenc.returncode != 0 and len(enc) == 0:
            raise RuntimeError(f"'wavpack' command \"{' '.join(cmd)}\" failed with error: {wavenc.stderr}")
        
        return enc

    def decode(self, buf, out=None):        
        cmd = copy(self.base_dec_cmd)

        # use pipe
        cmd += ["--raw", "-", "-o", "-"]
        
        if self.debug:
            print(" ".join(cmd), flush=True)

        # pipe buffer to wavpack stdin and return decoded in stdout
        wvdec = subprocess.run(cmd, input=buf, capture_output=True)
        dec = np.frombuffer(wvdec.stdout, dtype=self.dtype)
        
        if wvdec.returncode != 0 and len(dec) == 0:
            raise RuntimeError(f"'wvunpack' command \"{' '.join(cmd)}\" failed with error: {wvdec.stderr}")
        
        # handle output
        out = ndarray_copy(dec, out)
        
        return out
