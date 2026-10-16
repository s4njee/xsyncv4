// zstd on one 1 GiB file of large-text, from the lab job codec-levels (2026-10-16, run
// 20261016T201554Z-job-codec-levels): ratio, and MB/s compressing on 1 and 8 threads and
// decompressing on 1 (zstd -b, three passes). The Mac was busy (load average about 30), so its
// speeds vary from run to run; mars was idle. A fixed measurement, so it lives here as data.
export interface Level { ratio: number; compress1: number; compress8: number; decompress1: number }
export interface HostCodec { name: string; cores: number; note: string; levels: Record<1 | 2 | 3, Level> }

export const CODEC_RUN = { date: '16 October 2026', job: 'codec-levels', file: 'one 1 GiB file of large-text' };

export const CODEC: Record<'mars' | 'mac', HostCodec> = {
  mars: {
    name: 'mars', cores: 24, note: 'Ryzen 9 7900X, idle',
    levels: {
      1: { ratio: 2.793, compress1: 702.1, compress8: 4743.6, decompress1: 2749.2 },
      2: { ratio: 4.065, compress1: 711.6, compress8: 4673.9, decompress1: 2760.9 },
      3: { ratio: 4.230, compress1: 479.8, compress8: 3368.5, decompress1: 2567.2 },
    },
  },
  mac: {
    name: 'the Mac', cores: 10, note: 'M1 Max, load average about 30',
    levels: {
      1: { ratio: 2.793, compress1: 369.1, compress8: 1948.4, decompress1: 898.2 },
      2: { ratio: 4.065, compress1: 447.1, compress8: 1754.9, decompress1: 1503.5 },
      3: { ratio: 4.230, compress1: 284.6, compress8: 1231.4, decompress1: 1391.7 },
    },
  },
};
