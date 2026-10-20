import os
import certifi
import shutil

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import gradio_client
from gradio_client import handle_file

print("Conectando ao modelo de video de alta performance na nuvem...")
c = gradio_client.Client(
    'Lightricks/ltx-video-distilled',
    httpx_kwargs={"timeout": 300.0}
)

tasks = [
    {
        'idx': 2,
        'img': 'output/takes/take2.jpg',
        'prompt': 'Cinematic side profile of the man driving, wind blowing hair, warm golden hour sunset light, classic 1970 interior',
        'out': 'output/takes/take2_video.mp4'
    },
    {
        'idx': 3,
        'img': 'output/takes/take3.jpg',
        'prompt': 'Low-angle cinematic tracking shot of the vintage 1970 car speeding on the deserted Brasilia road, dust, glowing sunset',
        'out': 'output/takes/take3_video.mp4'
    }
]

for t in tasks:
    if os.path.exists(t['out']) and os.path.getsize(t['out']) > 10000:
        print(f"Take {t['idx']} já existe ({t['out']}), pulando...")
        continue
    print(f"Gerando Take {t['idx']} com LTX-Video...")
    res = c.predict(
        prompt=t['prompt'],
        negative_prompt='worst quality, inconsistent motion, blurry, jittery, distorted',
        input_image_filepath=handle_file(t['img']),
        input_video_filepath=None,
        height_ui=512,
        width_ui=704,
        mode='image-to-video',
        duration_ui=3.5,
        ui_frames_to_use=9,
        seed_ui=42 + t['idx'],
        randomize_seed=True,
        ui_guidance_scale=1.0,
        improve_texture_flag=True,
        api_name='/image_to_video'
    )
    video_path = res[0]['video']
    shutil.copy(video_path, t['out'])
    print(f"Take {t['idx']} salvo com sucesso em {t['out']}!")

print("Processo de geracao de takes finalizado!")
