import os
import sys
import argparse
import subprocess
import shutil

def main():
    parser = argparse.ArgumentParser(description='RVC VPS Studio Engine with RMVPE')
    parser.add_argument('--input', required=True, help='Path to input vocal/guide WAV')
    parser.add_argument('--model', required=True, help='Path to RVC .pth model')
    parser.add_argument('--index', default='', help='Path to .index file')
    parser.add_argument('--output', required=True, help='Path to output WAV')
    parser.add_argument('--pitch', type=int, default=0, help='Semitones shift (-12 to +12)')
    parser.add_argument('--method', default='rmvpe', help='Pitch method: rmvpe or pm')
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or '.', exist_ok=True)

    from infer_rvc_python.main import BaseLoader

    rmvpe_file = '/opt/rvc_models/rmvpe.pt' if os.path.exists('/opt/rvc_models/rmvpe.pt') else None
    hubert_file = '/opt/rvc_models/hubert_base.pt' if os.path.exists('/opt/rvc_models/hubert_base.pt') else None

    # Normaliza o áudio de entrada para 16kHz mono (requisito da rede neural RVC)
    out_dir = os.path.dirname(os.path.abspath(args.output)) or '/tmp'
    pre_wav = os.path.join(out_dir, f"rvc_pre_{os.path.basename(args.input)}.16k.wav")
    subprocess.run([
        'ffmpeg', '-y', '-i', args.input,
        '-ar', '16000', '-ac', '1',
        '-af', 'highpass=f=80,equalizer=f=3800:width_type=o:width=1.5:g=-2.0',
        pre_wav
    ], check=True, capture_output=True)

    chosen_algo = 'rmvpe' if (rmvpe_file and args.method == 'rmvpe') else 'pm'
    print(f"[RVC Engine] Carregando modelo com pitch_algo='{chosen_algo}' e RMVPE={bool(rmvpe_file)}...")

    loader = BaseLoader(
        only_cpu=True,
        hubert_path=None,  # Utiliza o repositório r3gm/hubert_base oficial compatível
        rmvpe_path=rmvpe_file
    )

    index_to_use = args.index if (args.index and os.path.exists(args.index)) else ''

    loader.apply_conf(
        tag='target_voice',
        file_model=args.model,
        pitch_algo=chosen_algo,
        pitch_lvl=args.pitch,
        file_index=index_to_use,
        index_influence=0.75
    )

    loader(
        audio_files=[pre_wav],
        tag_list=['target_voice'],
        type_output='wav'
    )

    res_path = loader.output_list[-1]
    if os.path.exists(res_path):
        # Pós-processamento anti-robótico: suaviza aspereza espectral (de-harshing) e normaliza a -1 dBFS
        post_cmd = [
            'ffmpeg', '-y', '-i', res_path,
            '-af', 'highpass=f=85,equalizer=f=3500:width_type=o:width=1.2:g=-1.8,loudnorm=I=-16:TP=-1.0:LRA=9',
            args.output
        ]
        subprocess.run(post_cmd, check=True, capture_output=True)
        if not (os.path.exists(args.output) and os.path.getsize(args.output) > 1000):
            shutil.copy(res_path, args.output)
    else:
        raise RuntimeError("RVC inference did not produce expected output file.")

    # Cleanup temp
    if os.path.exists(pre_wav):
        try: os.remove(pre_wav)
        except: pass

    print(f"[RVC Engine] Conversão com RMVPE concluída com sucesso: {args.output}")

if __name__ == '__main__':
    main()
