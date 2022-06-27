"""
Numcodecs Codec implementation for WavPack codec:
    
The (sub-optimal) approach is:
- for compression: to convert to the audio file and read it as the encoded bytes
- for decompression: dump the encoded data to a tmp file and decode it using the codec

Multi-channel data exceeding the number of channels that can be encoded by the codec are reshaped to fit the 
compression procedure.

"""
import numpy as np
import subprocess


from numcodecs.abc import Codec
from numcodecs.compat import ndarray_copy


##### NUMCODECS CODECS ######
class WavPackPipesCodec(Codec):    
    codec_id = "wavpackpipe"
    max_channels = 1024
    
    def __init__(self, compression_mode="default", 
                 hybrid_factor=None, cc=False, pair_unassigned=False, 
                 set_block_size=False, sample_rate=48000, 
                 dtype="int16"):
        self.compression_mode = compression_mode   
        self.cc = cc 
        self.hybrid_factor = hybrid_factor
        self.pair_unassigned = pair_unassigned
        self.set_block_size = set_block_size
        self.sample_rate = sample_rate
        self.dtype = dtype

        # prepare encode base command
        base_enc_cmd = ["wavpack", "-y"]
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
        self.base_dec_cmd = ["wvunpack", "-y", "-q"]

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
        print(" ".join(cmd))
        # pipe buffer to wavpack stdin and return stdout
        wavenc = subprocess.run(cmd, input=data.tobytes(), capture_output=True)
        enc = wavenc.stdout
        
        return enc

    def decode(self, buf, out=None):        
        cmd = self.base_dec_cmd

        # use pipe
        cmd += ["--raw", "-", "-o", "-"]
        print(" ".join(cmd))
        wvp = subprocess.run(cmd, input=buf, capture_output=True)
        dec = np.frombuffer(wvp.stdout, dtype=self.dtype)
        
        # handle output
        out = ndarray_copy(dec, out)
        
        return out


#### OLD
# from scipy.io import wavfile
# import time
# import tempfile


# # length of random string for tmp files
# RND_LEN = 10

# def get_random_string(length):
#     # choose from all lowercase letter
#     letters = string.ascii_lowercase
#     result_str = ''.join(random.choice(letters) for i in range(length))

#     return result_str


# class WavPackNumpyEncoder:
#     max_channels = 1024

#     def __init__(self,
#                  data,
#                  output_file,
#                  sample_rate,
#                  compression_mode="f",
#                  hybrid_factor=None,
#                  cc=False,
#                  pair_unassigned=False, 
#                  use_wav=True, 
#                  set_block_size=False, 
#                  ):
#         cformat = "wavpack"
#         assert data.shape[1] <= self.max_channels
#         assert compression_mode in ["f", "h", "hh", "default"]

#         self._data = data
#         self._nsamples, self._nchannels = data.shape
#         self._output_file = Path(output_file)
#         self._sample_rate = sample_rate
#         self._cmode = compression_mode
#         self._hybrid_factor = hybrid_factor
#         self._cc = cc
#         self._pair_unassigned = pair_unassigned
#         self._use_wav = use_wav
#         self._set_block_size = set_block_size
        
#     def process(self):
#         # approach: convert data to tmp wav file --> convert to wv --> rm wav
#         cmd = ["wavpack", "-y", "-q"]
#         if self._cmode in ["f", "h", "hh"]:
#             cmd += [f"-{self._cmode}"]
        
#         if self._hybrid_factor is not None:
#             cmd += [f"-b{self._hybrid_factor}"]
#             if self._cc:
#                 cmd += ["-cc"]
#         if self._pair_unassigned:
#             cmd += ["--pair-unassigned-chans"]
#         if self._set_block_size:
#             blocksize = min(self._nsamples, 131072)
#             cmd += [f"--blocksize={blocksize}"]
        
#         tmp_file = None

#         if self._use_wav:
#             tmp_file = self._output_file.parent / f"tmp{get_random_string(10)}.wav"
#             wavfile.write(tmp_file, int(self._sample_rate), self._data)    
#             cmd += ["-i", "-d"]
#             cmd += [str(tmp_file), "-o", str(self._output_file)]
#             subprocess.run(cmd, capture_output=False)
#             print(" ".join(cmd))
#         else:

#             cmd += [f"--raw-pcm={int(self._sample_rate)},16,{self._nchannels}"]
#             cmd += ["-", "-o", "-"] 
#             # pipe cat stout to wavpack stdin
#             input_data = self._data.tobytes()
#             wavp = subprocess.run(cmd, input=input_data, capture_output=True)

#             with self._output_file.open("wb") as f:
#                 f.write(wavp.stdout)
#             # self._data.tobytes()
#             # print(" ".join(pipe_cmd))
#             print(" ".join(cmd))
            
#         # rm tmp file
#         if tmp_file:
#             if tmp_file.is_file():
#                 tmp_file.unlink()
        

# class WavPackNumpyDecoder:
#     def __init__(self,
#                  input_file,
#                  use_wav=True,
#                  shape=None):
#         self._input_file = Path(input_file)
#         self._use_wav = use_wav
#         self._decoded_data = None
#         self._shape = shape

#     def process(self):
#         # convert to tmp wav file
#         cmd = ["wvunpack", "-y", "-q"]

#         if self._use_wav:
#             tmp_wav_file = self._input_file.parent / f"tmp{get_random_string(10)}.wav"

#             # print(f"Converting {self._input_file}")
#             cmd += [str(self._input_file), "-o", str(tmp_wav_file)]
#             subprocess.run(cmd, capture_output=False)
#             # load wav in memory
#             _, data = wavfile.read(tmp_wav_file)
        
#             # rm tmp wav file
#             tmp_wav_file.unlink()
#         else:
#             # use pipe
#             # cmd += [str(self._input_file), "--raw", "-o", "-"]
#             cmd += ["--raw", "-", "-o", "-"]
#             print(" ".join(cmd))
#             wvp = subprocess.run(cmd, input=self._input_file.open("rb").read(), capture_output=True) 
#             data = np.frombuffer(wvp.stdout, dtype="int16")
#             if self._shape:
#                 data = data.reshape(self._shape)

#         self._decoded_data = data

