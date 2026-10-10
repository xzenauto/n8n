import wave, numpy as np, sys
w = wave.open(sys.argv[1]); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768
hop = 128; fps = sr / hop
fr = np.lib.stride_tricks.sliding_window_view(x, 1024)[::hop]
S = np.abs(np.fft.rfft(fr * np.hanning(1024), axis=1))
flux = np.maximum(0, np.diff(np.log1p(S * 10), axis=0)).sum(1)
flux = np.maximum(0, flux - np.convolve(flux, np.ones(64) / 64, 'same'))
best = (0,)
for bpm in np.arange(105, 110, 0.005):
    per = 60 / bpm * fps
    for ph in np.arange(0, per, 1.0):
        idx = (ph + per * np.arange(int((len(flux) - ph) / per))).astype(int)
        sc = flux[idx].sum() + flux[np.minimum(idx + 1, len(flux) - 1)].sum()
        if sc > best[0]: best = (sc, bpm, ph / fps)
print("bpm %.3f fase %.4f" % best[1:])
