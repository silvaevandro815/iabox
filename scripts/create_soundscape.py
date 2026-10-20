import numpy as np
import soundfile as sf
import subprocess

sr = 44100
duration = 10.1
t = np.linspace(0, duration, int(sr * duration), endpoint=False)

# 1. Cinematic Sub-Bass / Drone (warm analog 55Hz A1 root note + 110Hz harmonic)
drone = 0.22 * np.sin(2 * np.pi * 55 * t) + 0.12 * np.sin(2 * np.pi * 110 * t)
# Add subtle slow modulation (LFO)
lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t)
drone = drone * (0.8 + 0.2 * lfo)

# 2. 1970 Classic V8 Engine Rumble (pulsing low-mid frequencies)
v8_freq = 28.0  # RPM idle/cruise rumble fundamental
v8 = 0.18 * np.sin(2 * np.pi * v8_freq * t)
v8 += 0.12 * np.sin(2 * np.pi * (v8_freq * 2) * t)
v8 += 0.08 * np.sin(2 * np.pi * (v8_freq * 4) * t)
v8 += 0.05 * np.sin(2 * np.pi * (v8_freq * 8) * t)
# Slight random rumble jitter
noise = np.random.normal(0, 0.03, len(t))
v8 = (v8 + noise) * 0.7

# 3. Wind Rush / Open Window (filtered white noise)
wind_raw = np.random.normal(0, 0.06, len(t))
# Simple moving average lowpass for gentle wind
window_size = 50
wind = np.convolve(wind_raw, np.ones(window_size)/window_size, mode='same')
# Fade in and out
fade_len = int(sr * 0.5)
fade_in = np.linspace(0, 1, fade_len)
fade_out = np.linspace(1, 0, fade_len)
wind[:fade_len] *= fade_in
wind[-fade_len:] *= fade_out

# Combine background sound design
ambience = drone + v8 + wind

# Normalize ambience to -18dB
max_val = np.max(np.abs(ambience))
if max_val > 0:
    ambience = ambience / max_val * 0.35

sf.write('output/takes/ambience.wav', ambience, sr)
print('Ambiente sonoro gerado com sucesso!')
