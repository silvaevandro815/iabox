import os
import sys
import argparse
from infer_rvc_python.main import BaseLoader

def main():
    parser = argparse.ArgumentParser(description='RVC VPS Runner')
    parser.add_argument('--input', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--index', default='')
    parser.add_argument('--output', required=True)
    parser.add_argument('--pitch', type=int, default=0)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)

    loader = BaseLoader(only_cpu=True, hubert_path=None, rmvpe_path='/opt/rvc_models/rmvpe.pt')
    loader.apply_conf(
        tag='target_voice',
        file_model=args.model,
        pitch_algo='pm',
        pitch_lvl=args.pitch,
        file_index=args.index,
        index_influence=0.75
    )

    loader(
        audio_files=[args.input],
        tag_list=['target_voice'],
        type_output='wav'
    )
    res_path = loader.output_list[-1]
    if os.path.exists(res_path) and res_path != args.output:
        import shutil
        shutil.move(res_path, args.output)
    print(f'RVC conversion successful: {args.output}')

if __name__ == '__main__':
    main()
