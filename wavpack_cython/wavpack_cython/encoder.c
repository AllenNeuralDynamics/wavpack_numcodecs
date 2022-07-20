// Demo program for in-memory WavPack encoding.

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "wavpack/wavpack.h"

// This is the callback required by the wavpack-stream library to write compressed audio frames.

typedef struct {
    size_t bytes_available, bytes_used;
    char *data, overflow;
} WavpackWriterContext;

static int write_block (void *id, void *data, int32_t length)
{
    WavpackWriterContext *cxt = id;

    if (!cxt->data || cxt->overflow)
        return 0;

    if (cxt->bytes_used + length > cxt->bytes_available) {
        length = cxt->bytes_available - cxt->bytes_used;
        cxt->overflow = 1;
        return 0;
    }

    memcpy (cxt->data + cxt->bytes_used, data, length);
    cxt->bytes_used += length;
    return 1;
}

// This is the single function for completely encoding a WavPack file from memory to memory. This version is
// for 16-bit audio in any number of channels. The level parameter is the speed mode, from 1 - 4. The bps
// parameter is the number of bits to allocate for each sample (minimum: about 2.25) which should be set
// to 0.0 for lossless encoding. The destination must be large enough for the entire file (be conservative).
// The return value is the number of bytes generated, or -1 if there was not enough space to encode to
// (or some other error).

#define BUFFER_SAMPLES 256

size_t WavpackEncodeFile (void *source_char, size_t num_samples, size_t num_chans, int level, float bps, void *destin, size_t destin_bytes)
{
    int16_t *source = source_char;
    size_t num_samples_remaining = num_samples;
    int32_t *temp_buffer = NULL;
    WavpackWriterContext raw_wv;
    WavpackConfig config;
    WavpackContext *wpc;

    memset (&raw_wv, 0, sizeof (WavpackWriterContext));
    raw_wv.bytes_available = destin_bytes;
    raw_wv.data = destin;

    wpc = WavpackOpenFileOutput (write_block, &raw_wv, NULL);

    if (!wpc) {
        fprintf (stderr, "could not create WavPack context\n");
        return -1;
    }

    memset (&config, 0, sizeof (WavpackConfig));
    config.num_channels = num_chans;
    config.bytes_per_sample = 2;
    config.bits_per_sample = 16;
    config.sample_rate = 32000;     // doesn't need to be correct, although it might be nice

    config.block_samples = num_samples;

    while (config.block_samples > 120000)
        config.block_samples = (config.block_samples + 1) >> 1;

    config.flags = CONFIG_PAIR_UNDEF_CHANS;

    if (level == 1)
        config.flags |= CONFIG_FAST_FLAG;
    else if (level == 3)
        config.flags |= CONFIG_HIGH_FLAG;
    else if (level == 4)
        config.flags |= CONFIG_HIGH_FLAG | CONFIG_VERY_HIGH_FLAG;
    else if (level != 2) {
        fprintf (stderr, "WavPack configuration error (level = %d, range = 1-4)\n", level);
        WavpackCloseFile (wpc);
        return -1;
    }

    if (bps > 0.0) {
        config.flags = CONFIG_HYBRID_FLAG;
        config.bitrate = bps;
    }

    if (!WavpackSetConfiguration (wpc, &config, num_samples)) {
        fprintf (stderr, "WavPack configuration error\n");
        WavpackCloseFile (wpc);
        return -1;
    }

    if (!WavpackPackInit (wpc)) {
        fprintf (stderr, "WavPack initialization failed\n");
        WavpackCloseFile (wpc);
        return -1;
    }

    temp_buffer = malloc (BUFFER_SAMPLES * num_chans * sizeof (int32_t));

    while (num_samples_remaining) {
        int samples_to_encode = num_samples_remaining < BUFFER_SAMPLES ?
            num_samples_remaining :
            BUFFER_SAMPLES;
        int samples_to_copy = samples_to_encode * num_chans;
        int32_t *dptr = temp_buffer;

        while (samples_to_copy--)
            *dptr++ = *source++;

        if (!WavpackPackSamples (wpc, temp_buffer, samples_to_encode)) {
            fprintf (stderr, "WavPack encoding failed\n");
            free (temp_buffer);
            WavpackCloseFile (wpc);
            return -1;
        }

        num_samples_remaining -= samples_to_encode;
    }

    free (temp_buffer);
        
    if (!WavpackFlushSamples (wpc)) {
        fprintf (stderr, "WavPack flush failed\n");
        WavpackCloseFile (wpc);
        return -1;
    }

    WavpackCloseFile (wpc);

    return raw_wv.overflow ? -1 : raw_wv.bytes_used;
}
