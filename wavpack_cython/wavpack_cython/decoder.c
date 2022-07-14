// Demo program for in-memory WavPack decoding.

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "wavpack/wavpack.h"

// This is the context for reading a memory-based "file"

typedef struct {
    unsigned char ungetc_char, ungetc_flag;
    unsigned char *sptr, *dptr, *eptr;
    int64_t total_bytes_read;
} WavpackReaderContext;

static int32_t raw_read_bytes (void *id, void *data, int32_t bcount)
{
    WavpackReaderContext *rcxt = (WavpackReaderContext *) id;
    unsigned char *outptr = (unsigned char *) data;

    while (bcount) {
        if (rcxt->ungetc_flag) {
            *outptr++ = rcxt->ungetc_char;
            rcxt->ungetc_flag = 0;
            bcount--;
        }
        else {
            size_t bytes_to_copy = rcxt->eptr - rcxt->dptr;

            if (!bytes_to_copy)
                break;

            if (bytes_to_copy > bcount)
                bytes_to_copy = bcount;

            memcpy (outptr, rcxt->dptr, bytes_to_copy);
            rcxt->total_bytes_read += bytes_to_copy;
            rcxt->dptr += bytes_to_copy;
            outptr += bytes_to_copy;
            bcount -= bytes_to_copy;
        }
    }

    return (int32_t)(outptr - (unsigned char *) data);
}

static int32_t raw_write_bytes (void *id, void *data, int32_t bcount)
{
    return 0;
}

static int64_t raw_get_pos (void *id)
{
    WavpackReaderContext *rcxt = (WavpackReaderContext *) id;
    return rcxt->dptr - rcxt->sptr;
}

static int raw_set_pos_abs (void *id, int64_t pos)
{
    return 1;
}

static int raw_set_pos_rel (void *id, int64_t delta, int mode)
{
    return 1;
}

static int raw_push_back_byte (void *id, int c)
{
    WavpackReaderContext *rcxt = (WavpackReaderContext *) id;
    rcxt->ungetc_char = c;
    rcxt->ungetc_flag = 1;
    return c;
}

static int64_t raw_get_length (void *id)
{
    return 0;
}

static int raw_can_seek (void *id)
{
    return 0;
}

static int raw_close_stream (void *id)
{
    return 0;
}

static WavpackStreamReader64 raw_reader = {
    raw_read_bytes, raw_write_bytes, raw_get_pos, raw_set_pos_abs, raw_set_pos_rel,
    raw_push_back_byte, raw_get_length, raw_can_seek, NULL, raw_close_stream
};

// This is the single function for completely decoding a WavPack file from memory to memory. This version is
// for 16-bit audio in any number of channels, and will error out if the source file is not 16-bit. The
// number of channels is written to the specified pointer, but it is assumed that the caller already knows
// this. The number of composite samples (i.e., frames) is returned.

#define BUFFER_SAMPLES 256

size_t WavpackDecodeFile (void *source, size_t source_bytes, int16_t *num_chans, void *destin_char, size_t destin_bytes)
{
    int16_t *destin = destin_char;
    size_t total_samples = 0, max_samples;
    int32_t *temp_buffer = NULL;
    WavpackReaderContext raw_wv;
    WavpackContext *wpc;
    char error [80];
    int nch, bps;

    memset (&raw_wv, 0, sizeof (WavpackReaderContext));
    raw_wv.dptr = raw_wv.sptr = (unsigned char *) source;
    raw_wv.eptr = raw_wv.dptr + source_bytes;
    wpc = WavpackOpenFileInputEx64 (&raw_reader, &raw_wv, NULL, error, OPEN_STREAMING, 0);

    if (!wpc) {
        fprintf (stderr, "error opening file: %s\n", error);
        return -1;
    }

    nch = WavpackGetNumChannels (wpc);
    bps = WavpackGetBytesPerSample (wpc);

    if (bps != 2) {
        fprintf (stderr, "error opening file: bytes/sample = %d\n", bps);
        return -1;
    }

    if (num_chans)
        *num_chans = nch;

    max_samples = destin_bytes / sizeof (int16_t) / nch;
    temp_buffer = malloc (BUFFER_SAMPLES * nch * sizeof (int32_t));

    while (1) {
        int samples_to_decode = total_samples + BUFFER_SAMPLES > max_samples ?
            max_samples - total_samples :
            BUFFER_SAMPLES;
        int samples_decoded = WavpackUnpackSamples (wpc, temp_buffer, samples_to_decode);
        int samples_to_copy = samples_decoded * nch;
        int32_t *sptr = temp_buffer;

        if (!samples_decoded)
            break;

        while (samples_to_copy--)
            *destin++ = *sptr++;

        if ((total_samples += samples_decoded) == max_samples)
            break;
    }

    free (temp_buffer);
    WavpackCloseFile (wpc);
    return total_samples;
}

// This is the demo program for decoding a 16-bit WavPack file in memory. The input file is presented
// to stdin and completely read. Then the decoder above is called to decode the file in memory, and
// then the resulting samples are written to stdout.

#define OUTBUFFER_SIZE (20000000 * sizeof (int16_t))
#define INBUFFER_SIZE 65536

// int main (void)
// {
//     int16_t *decode_buffer = malloc (OUTBUFFER_SIZE), num_chans;
//     size_t inbuffer_size = INBUFFER_SIZE, infile_size = 0;
//     unsigned char *infile_buffer = malloc (INBUFFER_SIZE);
//     size_t decoded_samples;
//     int times = 1, ch;

//     // first, read stdin until it reaches EOF

//     while ((ch = getchar()) != EOF) {
//         infile_buffer [infile_size++] = ch;

//         if (infile_size == inbuffer_size)
//             infile_buffer = realloc (infile_buffer, inbuffer_size += INBUFFER_SIZE);
//     }

//     if (infile_size < 32) {
//         fprintf (stderr, "input too small to be WavPack: %zu bytes\n", infile_size);
//         free (infile_buffer);
//         return 1;
//     }

//     fprintf (stderr, "input file size = %zu bytes\n", infile_size);
//     decode_buffer = malloc (OUTBUFFER_SIZE);

//     // now decode the file, perhaps multiple times (to test for memory leaks or measure performance)

//     while (times--)
//         decoded_samples = WavpackDecodeFile (infile_buffer, infile_size, &num_chans, decode_buffer, OUTBUFFER_SIZE);

//     free (infile_buffer);

//     if (decoded_samples == (size_t) -1) {
//         fprintf (stderr, "WavpackDecodeFile() returned error\n");
//         free (decode_buffer);
//         return 1;
//     }

//     // now write the results to stdout

//     fwrite (decode_buffer, sizeof (int16_t) * num_chans, decoded_samples, stdout);
//     free (decode_buffer);

//     // finally, report the results to stderr

//     fprintf (stderr, "num channels = %d, decoded_samples = %zu\n", num_chans, decoded_samples);
//     fprintf (stderr, "output file size = %zu bytes\n", num_chans * decoded_samples * sizeof (int16_t));
//     return 0;
// }
