"""
Numcodecs Codec implementation for WavPack (https://www.wavpack.com/) codec.

**implementation detils**

Multi-channel data exceeding the number of channels (or more than 2d) are flattened.
"""
import numpy as np
import subprocess
import platform
from pathlib import Path

from numcodecs.abc import Codec
from numcodecs.compat import ndarray_copy


lib_folder = Path(__file__).parent.parent / "lib"

if platform.system() == "Linux":
    wavpack_cmd = str((lib_folder / "linux" / "wavpack").resolve().absolute())
    wvunpack_cmd = str((lib_folder / "linux" / "wvunpack").resolve().absolute())
elif platform.system() == "macOS":
    wavpack_cmd = str((lib_folder / "macos" / "wavpack").resolve().absolute())
    wvunpack_cmd = str((lib_folder / "macos" / "wvunpack").resolve().absolute())
else: # windows
    wavpack_cmd = str((lib_folder / "windows" / "wavpack.exe").resolve().absolute())
    wvunpack_cmd = str((lib_folder / "windows" / "wvunpack.exe").resolve().absolute())


class WavPackPipesCodec(Codec):    
    codec_id = "wavpackpipe"
    max_channels = 1024
    
    def __init__(self, compression_mode="default", 
                 hybrid_factor=None, cc=False, pair_unassigned=False, 
                 set_block_size=False, sample_rate=48000, 
                 dtype="int16"):
        """_summary_

        Parameters
        ----------
        compression_mode : str, optional
            _description_, by default "default"
        hybrid_factor : _type_, optional
            _description_, by default None
        cc : bool, optional
            _description_, by default False
        pair_unassigned : bool, optional
            _description_, by default False
        set_block_size : bool, optional
            _description_, by default False
        sample_rate : int, optional
            _description_, by default 48000
        dtype : str, optional
            _description_, by default "int16"
        """
        self.compression_mode = compression_mode   
        self.cc = cc 
        self.hybrid_factor = hybrid_factor
        self.pair_unassigned = pair_unassigned
        self.set_block_size = set_block_size
        self.sample_rate = sample_rate
        self.dtype = dtype

        # prepare encode base command
        base_enc_cmd = [wavpack_cmd, "-y"]
        if self.compression_mode in ["f", "h", "hh"]:
            base_enc_cmd += [f"-{compression_mode}"]
        if self.hybrid_factor is not None:
            base_enc_cmd += [f"-b{hybrid_factor}"]
            if self._cc:
                base_enc_cmd += ["-cc"]
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
            cc=self.cc,
            hybrid_factor=self.hybrid_factor,
            pair_unassigned=self.pair_unassigned,
            set_block_size=self.set_block_size,
            sample_rate=self.sample_rate,
            dtype=self.dtype,
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
        cmd = self.base_enc_cmd
        data = self._prepare_data(buf)
        nsamples, nchans = data.shape
        nbits = int(data.dtype.itemsize * 8)

        if self.set_block_size:
            blocksize = min(nsamples, 131072)
            cmd += [f"--blocksize={blocksize}"]
        
        cmd += [f"--raw-pcm={int(self.sample_rate)},{nbits},{nchans}"]
        cmd += ["-q", "-", "-o", "-"] 
        # pipe buffer to wavpack stdin and return encoded in stdout
        wavenc = subprocess.run(cmd, input=data.tobytes(), capture_output=True)
        enc = wavenc.stdout
        
        return enc

    def decode(self, buf, out=None):        
        cmd = self.base_dec_cmd

        # use pipe
        cmd += ["--raw", "-", "-o", "-"]
        # pipe buffer to wavpack stdin and return decoded in stdout
        wvp = subprocess.run(cmd, input=buf, capture_output=True)
        dec = np.frombuffer(wvp.stdout, dtype=self.dtype)
        
        # handle output
        out = ndarray_copy(dec, out)
        
        return out
