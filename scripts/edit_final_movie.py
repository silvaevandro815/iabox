import subprocess
import os

base_dir = r"C:\Users\User\Desktop\Editor de Video IA"
ffmpeg_exe = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"

takes_dir = os.path.join(base_dir, "output", "takes")
concat_txt = os.path.join(takes_dir, "concat_list.txt")

with open(concat_txt, "w") as f:
    f.write("file 'take1_video.mp4'\n")
    f.write("file 'take2_video.mp4'\n")
    f.write("file 'take3_video.mp4'\n")

audio_file = os.path.join(takes_dir, "soundtrack_master.aac")
output_final = os.path.join(base_dir, "output", "evandro_brasilia_1970.mp4")

cmd = [
    ffmpeg_exe, "-y",
    "-f", "concat", "-safe", "0", "-i", concat_txt,
    "-i", audio_file,
    "-vf", (
        "scale=1280:720:flags=lanczos,"
        "eq=contrast=1.08:brightness=0.01:saturation=1.12,"
        "noise=c1s=3:c0f=u,"
        "format=yuv420p"
    ),
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "18",
    "-c:a", "aac",
    "-b:a", "256k",
    "-shortest",
    output_final
]

print("Renderizando o filme final cinematográfico...")
res = subprocess.run(cmd, capture_output=True, text=True, cwd=takes_dir)

if res.returncode == 0:
    print(f"Filme renderizado com sucesso absoluto: {output_final}")
else:
    print("Erro:", res.stderr)
