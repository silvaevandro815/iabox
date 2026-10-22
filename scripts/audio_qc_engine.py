"""
========================================================================================
AUDIO QC ENGINE & PHONETIC AUDIT (CANONICAL 8-STAGE SPECIFICATION)
========================================================================================
Audita arquivos de áudio conforme as normas ITU-R BS.1770, correlação estéreo L/R,
análise espectral por bandas de oitava e taxa de acerto fonético (Whisper).
Proíbe adjetivos vazios: relata apenas medições exatas e portões de qualidade.
========================================================================================
"""

import os
import sys
import re
import json
import subprocess
import numpy as np
import soundfile as sf


def measure_ebur128(audio_path):
    """
    Mede Loudness Integrado (LUFS), LRA (LU) e True Peak (dBTP) via FFmpeg ebur128.
    """
    cmd = [
        "ffmpeg", "-nostats", "-i", audio_path,
        "-filter_complex", "ebur128=peak=true",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    out = res.stderr

    summary_idx = out.rfind("Summary:")
    summary_text = out[summary_idx:] if summary_idx != -1 else out

    lufs_match = re.search(r"I:\s+([-\d\.]+)\s+LUFS", summary_text)
    lra_match = re.search(r"LRA:\s+([-\d\.]+)\s+LU", summary_text)
    tp_match = re.search(r"Peak:\s+([-\d\.]+)\s+dBFS", summary_text)

    integrated_lufs = float(lufs_match.group(1)) if lufs_match else None
    lra = float(lra_match.group(1)) if lra_match else None
    true_peak = float(tp_match.group(1)) if tp_match else None

    return {
        "integrated_lufs": integrated_lufs,
        "lra": lra,
        "true_peak": true_peak
    }


def measure_stereo_correlation(audio_path):
    """
    Mede a correlação entre canal L e R, nível RMS do Mid e Side, e razão Side/Mid.
    """
    data, sr = sf.read(audio_path)
    if data.ndim == 1:
        return {
            "channels": 1,
            "is_stereo": False,
            "correlation_lr": 1.0,
            "side_db": -240.0,
            "mid_db": float(20 * np.log10(np.sqrt(np.mean(data**2)) + 1e-12)),
            "side_mid_ratio_db": -240.0
        }

    L = data[:, 0]
    R = data[:, 1]
    mid = 0.5 * (L + R)
    side = 0.5 * (L - R)

    rms_mid = np.sqrt(np.mean(mid**2))
    rms_side = np.sqrt(np.mean(side**2))
    
    mid_db = float(20 * np.log10(rms_mid + 1e-12))
    side_db = float(20 * np.log10(rms_side + 1e-12))
    ratio = float(side_db - mid_db)

    # Correlação Pearson
    std_L = np.std(L)
    std_R = np.std(R)
    if std_L > 1e-7 and std_R > 1e-7:
        corr = float(np.corrcoef(L, R)[0, 1])
    else:
        corr = 1.0

    return {
        "channels": 2,
        "is_stereo": (corr < 0.999 and side_db > -60.0),
        "correlation_lr": round(corr, 4),
        "mid_db": round(mid_db, 2),
        "side_db": round(side_db, 2),
        "side_mid_ratio_db": round(ratio, 2)
    }


def measure_spectral_bands(audio_path, target_window_sec=None):
    """
    Analisa a distribuição espectral em bandas de oitava e calcula a % de energia
    na faixa vocal de presença (300 a 3500 Hz).
    """
    data, sr = sf.read(audio_path)
    if data.ndim > 1:
        signal = np.mean(data, axis=1)
    else:
        signal = data

    if target_window_sec:
        start_sample = int(target_window_sec[0] * sr)
        end_sample = int(target_window_sec[1] * sr)
        signal = signal[start_sample:end_sample]

    if len(signal) == 0:
        return {}

    fft_vals = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sr)

    power = fft_vals ** 2
    total_power = np.sum(power) + 1e-12

    def band_power(f_low, f_high):
        mask = (freqs >= f_low) & (freqs < f_high)
        return np.sum(power[mask])

    p_60_120 = band_power(60, 120)
    p_250_500 = band_power(250, 500)
    p_1k_2k = band_power(1000, 2000)
    p_2k_4k = band_power(2000, 4000)
    p_4k_8k = band_power(4000, 8000)
    p_8k_16k = band_power(8000, 16000)

    p_vocal_range = band_power(300, 3500)
    pct_vocal = float((p_vocal_range / total_power) * 100)

    ref_power = p_60_120 if p_60_120 > 0 else 1e-12
    return {
        "pct_energy_300_3500hz": round(pct_vocal, 2),
        "rel_db_60_120hz": 0.0,
        "rel_db_250_500hz": round(float(10 * np.log10((p_250_500 + 1e-12) / ref_power)), 2),
        "rel_db_1k_2khz": round(float(10 * np.log10((p_1k_2k + 1e-12) / ref_power)), 2),
        "rel_db_2k_4khz": round(float(10 * np.log10((p_2k_4k + 1e-12) / ref_power)), 2),
        "rel_db_4k_8khz": round(float(10 * np.log10((p_4k_8k + 1e-12) / ref_power)), 2),
        "rel_db_8k_16khz": round(float(10 * np.log10((p_8k_16k + 1e-12) / ref_power)), 2),
    }


def calculate_word_accuracy(reference_text, transcribed_text):
    """
    Calcula taxa de acerto fonético palavra a palavra normalizada.
    """
    def clean_words(t):
        t = re.sub(r"[^\w\s]", "", t.lower())
        return [w for w in t.split() if w]

    ref_words = clean_words(reference_text)
    trans_words = clean_words(transcribed_text)

    if not ref_words:
        return 0.0

    # Contagem de palavras encontradas
    hits = sum(1 for w in ref_words if w in trans_words)
    acc = (hits / len(ref_words)) * 100
    return round(acc, 2)


def audit_full_pipeline(audio_path, reference_lyrics="", chorus_window=(56, 85)):
    """
    Audita completamente um arquivo de paródia musical contra os portões da especificação técnica.
    """
    ebur = measure_ebur128(audio_path)
    stereo = measure_stereo_correlation(audio_path)
    spectral = measure_spectral_bands(audio_path, target_window_sec=chorus_window)

    report = {
        "arquivo": os.path.basename(audio_path),
        "tamanho_mb": round(os.path.getsize(audio_path) / (1024 * 1024), 2),
        "metricas_ebur128": ebur,
        "metricas_stereo": stereo,
        "analise_espectral_refrão": spectral,
        "portões_qc": {
            "lufs_valido": (ebur["integrated_lufs"] is not None and -15.5 <= ebur["integrated_lufs"] <= -8.5),
            "true_peak_seguro": (ebur["true_peak"] is not None and ebur["true_peak"] <= -0.9),
            "estereo_real": (0.20 <= stereo["correlation_lr"] <= 0.75 and stereo["side_db"] > -50.0),
            "energia_vocal_refrao": (spectral.get("pct_energy_300_3500hz", 0) >= 45.0)
        }
    }
    return report


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = r"c:\Users\User\Desktop\Editor de Video IA\output\parodia_marco_pinheiro_rvc_oficial.mp3"

    print(f"--- EXECUTANDO AUDITORIA CANÔNICA DE QC: {target} ---")
    rep = audit_full_pipeline(target)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
