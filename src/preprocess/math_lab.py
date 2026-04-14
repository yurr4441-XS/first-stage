import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 2 * np.pi, 2000)

signal = np.sin(2 * x) + 0.5 * np.sin(6 * x) + 0.2 * np.sin(15 * x)

# FFT
fft_vals = np.fft.fft(signal)
freqs = np.fft.fftfreq(len(signal), d=(x[1] - x[0]))

# 只看正频率
mask = freqs > 0
freqs_positive = freqs[mask]
amplitude = np.abs(fft_vals[mask])

fft_vals_filtered = fft_vals.copy()

# 只保留低频（例如前10个）
fft_vals_filtered[10:-10] = 0

signal_filtered = np.fft.ifft(fft_vals_filtered)

plt.figure(figsize=(12,6))
plt.plot(x, signal, label='Original')
plt.plot(x, signal_filtered.real, label='Filtered (low freq only)')
plt.legend()
plt.grid(True)
plt.show()