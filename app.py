"""
========================================================================================
IABOX — Servidor Central e API de IA (FastAPI)
Domínio: iabox.evandrosilvagallina.cloud
Criador: Evandro Silva Gallina
========================================================================================
"""

import os
import sys
import uuid
import time
import json
import sqlite3
import shutil
import asyncio
import subprocess
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values

# Carrega variáveis de ambiente
env = dotenv_values('.env')
if not env:
    env = os.environ

STRIPE_SECRET_KEY = env.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = env.get('STRIPE_PUBLISHABLE_KEY', '')
GEMINI_API_KEY = env.get('GEMINI_API_KEY', '') or env.get('GOOGLE_API_KEY', '')

# Inicialização do FastAPI
app = FastAPI(
    title="IABOX — Plataforma de Criação e Edição com IA",
    description="Motor All-in-One de Vídeos Virais, Locuções PT-BR, Clonagem Vocal, Suno Music Studio e Paródias.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
STATIC_DIR = "static"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Banco de Dados SQLite Local
DATA_DIR = os.environ.get("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "iabox.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT,
            credits INTEGER DEFAULT 50,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            amount_brl REAL,
            credits INTEGER,
            status TEXT,
            stripe_session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            type TEXT,
            status TEXT,
            progress INTEGER DEFAULT 0,
            result_url TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user_credits(user_id="default_user"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT credits FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (id, credits) VALUES (?, ?)", (user_id, 0)) # Saldo 0: requer compra pré-paga
        conn.commit()
        credits = 0
    else:
        credits = row[0]
    conn.close()
    return credits

def deduct_credits(user_id="default_user", amount=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    current = get_user_credits(user_id)
    if current < amount:
        conn.close()
        return False
    c.execute("UPDATE users SET credits = credits - ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return True

def add_credits(user_id="default_user", amount=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def save_job(job_id, job_type, status="processing", progress=10, result_url=None, error=None, user_id="default_user"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO jobs (id, user_id, type, status, progress, result_url, error) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (job_id, user_id, job_type, status, progress, result_url, error))
    conn.commit()
    conn.close()

# Servir arquivos estáticos do Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/api/user/credits")
def get_credits(user_id: str = "default_user"):
    return {"user_id": user_id, "credits": get_user_credits(user_id)}

@app.get("/api/jobs/{job_id}")
def check_job(job_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT type, status, progress, result_url, error FROM jobs WHERE id = ?", (job_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return {
        "job_id": job_id,
        "type": row[0],
        "status": row[1],
        "progress": row[2],
        "result_url": row[3],
        "error": row[4]
    }

# ----------------------------------------------------------------------------------------
# 1. VOZES NEURAIS DO BRASIL (EDGE-TTS PT-BR)
# ----------------------------------------------------------------------------------------
@app.post("/api/voice/generate")
async def generate_voice(
    text: str = Form(...),
    voice: str = Form("antonio"),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=1):
        raise HTTPException(status_code=402, detail="Saldo de créditos insuficiente. Faça uma recarga.")

    job_id = str(uuid.uuid4())
    out_filename = f"voice_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    save_job(job_id, "voice", status="processing", progress=30)

    try:
        from scripts.voice_clone_engine import VoiceCloneEngine
        engine = VoiceCloneEngine()
        engine.generate_neural_brazil(text, output_path=out_path, voice=voice)
        save_job(job_id, "voice", status="completed", progress=100, result_url=f"/output/{out_filename}")
        return {"status": "success", "job_id": job_id, "result_url": f"/output/{out_filename}", "remaining_credits": get_user_credits(user_id)}
    except Exception as e:
        save_job(job_id, "voice", status="failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------------
# 2. CLONAGEM DE VOZ INSTANTÂNEA (1 MINUTO)
# ----------------------------------------------------------------------------------------
@app.post("/api/voice/clone")
async def clone_voice(
    text: str = Form(...),
    audio_sample: UploadFile = File(...),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=5):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 5 créditos).")

    job_id = str(uuid.uuid4())
    ref_filename = f"sample_{job_id[:8]}_{audio_sample.filename}"
    ref_path = os.path.join(UPLOAD_DIR, ref_filename)

    with open(ref_path, "wb") as f:
        shutil.copyfileobj(audio_sample.file, f)

    out_filename = f"cloned_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    save_job(job_id, "clone", status="processing", progress=20)

    try:
        from scripts.voice_clone_engine import VoiceCloneEngine
        engine = VoiceCloneEngine()
        engine.clone_voice_sample(ref_path, text, output_path=out_path)
        save_job(job_id, "clone", status="completed", progress=100, result_url=f"/output/{out_filename}")
        return {"status": "success", "job_id": job_id, "result_url": f"/output/{out_filename}", "remaining_credits": get_user_credits(user_id)}
    except Exception as e:
        save_job(job_id, "clone", status="failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------------
# 3. SUNO STUDIO — MÚSICAS INÉDITAS DO ZERO
# ----------------------------------------------------------------------------------------
@app.post("/api/music/suno")
async def generate_suno_music(
    theme: str = Form(...),
    genre: str = Form("sertanejo pop animado, violao, sanfona e bateria"),
    duration: int = Form(95),
    voice_sample: Optional[UploadFile] = File(None),
    user_id: str = Form("default_user")
):
    cost = 20 if voice_sample else 15
    if not deduct_credits(user_id, amount=cost):
        raise HTTPException(status_code=402, detail=f"Saldo insuficiente (necessário {cost} créditos).")

    job_id = str(uuid.uuid4())
    save_job(job_id, "suno", status="processing", progress=15)

    voice_path = None
    if voice_sample:
        voice_path = os.path.join(UPLOAD_DIR, f"voice_{job_id[:8]}_{voice_sample.filename}")
        with open(voice_path, "wb") as f:
            shutil.copyfileobj(voice_sample.file, f)

    out_filename = f"suno_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    def _task():
        try:
            import importlib
            mod = importlib.import_module("scripts.10_suno_studio_engine")
            engine = mod.SunoStudioEngine()
            lyrics = engine.compose_lyrics(theme, genre=genre, duration_sec=duration)
            save_job(job_id, "suno", status="processing", progress=40)

            raw_song = engine.generate_full_song(lyrics, style_prompt=genre, output_path=os.path.join(OUTPUT_DIR, f"raw_{out_filename}"), duration=duration)
            save_job(job_id, "suno", status="processing", progress=75)

            if voice_path:
                engine.clone_singer_on_song(raw_song, voice_path, output_path=out_path)
            else:
                shutil.copy(raw_song, out_path)

            save_job(job_id, "suno", status="completed", progress=100, result_url=f"/output/{out_filename}")
        except Exception as e:
            save_job(job_id, "suno", status="failed", error=str(e))

    import threading
    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": "Geração musical iniciada em segundo plano.", "cost": cost}

# ----------------------------------------------------------------------------------------
# 4. PARÓDIAS & AI SONG COVERS
# ----------------------------------------------------------------------------------------
@app.post("/api/music/parody")
async def create_parody(
    song_file: UploadFile = File(...),
    guide_file: UploadFile = File(...),
    voice_sample: UploadFile = File(...),
    pitch_shift: int = Form(0),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=20):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 20 créditos).")

    job_id = str(uuid.uuid4())
    save_job(job_id, "parody", status="processing", progress=15)

    song_path = os.path.join(UPLOAD_DIR, f"song_{job_id[:8]}_{song_file.filename}")
    guide_path = os.path.join(UPLOAD_DIR, f"guide_{job_id[:8]}_{guide_file.filename}")
    voice_path = os.path.join(UPLOAD_DIR, f"voice_{job_id[:8]}_{voice_sample.filename}")

    with open(song_path, "wb") as f: shutil.copyfileobj(song_file.file, f)
    with open(guide_path, "wb") as f: shutil.copyfileobj(guide_file.file, f)
    with open(voice_path, "wb") as f: shutil.copyfileobj(voice_sample.file, f)

    out_filename = f"parodia_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    def _task():
        try:
            import importlib
            mod = importlib.import_module("scripts.10_suno_studio_engine")
            engine = mod.SunoStudioEngine()
            engine.create_parody(
                original_song_path=song_path,
                parody_vocal_guide=guide_path,
                user_voice_path=voice_path,
                output_path=out_path,
                pitch_shift=pitch_shift
            )
            save_job(job_id, "parody", status="completed", progress=100, result_url=f"/output/{out_filename}")
        except Exception as e:
            save_job(job_id, "parody", status="failed", error=str(e))

    import threading
    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": "Criação de paródia iniciada.", "cost": 20}

# ----------------------------------------------------------------------------------------
# 5. GERADOR DE IMAGENS & CRIATIVOS PUBLICITÁRIOS (FLUX / POLLINATIONS)
# ----------------------------------------------------------------------------------------
@app.post("/api/image/generate")
async def generate_image(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=2):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 2 créditos).")

    job_id = str(uuid.uuid4())
    dim_map = {
        "1:1": (1024, 1024),
        "9:16": (768, 1344),
        "16:9": (1344, 768)
    }
    w, h = dim_map.get(aspect_ratio, (1024, 1024))
    out_filename = f"image_{job_id[:8]}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    import urllib.parse
    import requests
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true&enhance=true&model=flux"

    try:
        r = requests.get(url, timeout=45)
        if r.status_code == 200:
            with open(out_path, "wb") as f:
                f.write(r.content)
            save_job(job_id, "image", status="completed", progress=100, result_url=f"/output/{out_filename}")
            return {"status": "success", "job_id": job_id, "result_url": f"/output/{out_filename}", "remaining_credits": get_user_credits(user_id)}
        else:
            raise RuntimeError(f"Erro no provedor de imagem: status {r.status_code}")
    except Exception as e:
        save_job(job_id, "image", status="failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------------
# 6. EDITOR DE VÍDEOS VIRAIS (REELS/SHORTS 9:16)
# ----------------------------------------------------------------------------------------
@app.post("/api/video/edit")
async def edit_viral_video(
    video_file: UploadFile = File(...),
    silence_removal: bool = Form(True),
    subtitles_karaoke: bool = Form(True),
    punch_zoom: bool = Form(True),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=10):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 10 créditos).")

    job_id = str(uuid.uuid4())
    in_filename = f"raw_video_{job_id[:8]}_{video_file.filename}"
    in_path = os.path.join(UPLOAD_DIR, in_filename)

    with open(in_path, "wb") as f:
        shutil.copyfileobj(video_file.file, f)

    out_filename = f"viral_{job_id[:8]}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    save_job(job_id, "video", status="processing", progress=20)

    def _task():
        try:
            save_job(job_id, "video", status="processing", progress=40)
            vf_filters = [
                "scale=1080:1920:force_original_aspect_ratio=increase",
                "crop=1080:1920",
                "eq=contrast=1.06:brightness=0.02:saturation=1.12",
                "format=yuv420p"
            ]
            vf_str = ",".join(vf_filters)
            af_str = "silenceremove=start_periods=1:start_duration=0.25:start_threshold=-35dB:detection=peak" if silence_removal else "anull"

            cmd = [
                "ffmpeg", "-y",
                "-i", in_path,
                "-vf", vf_str,
                "-af", af_str,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "21",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                out_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(out_path):
                save_job(job_id, "video", status="completed", progress=100, result_url=f"/output/{out_filename}")
            else:
                fallback_cmd = [
                    "ffmpeg", "-y", "-i", in_path,
                    "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
                    "-c:v", "libx264", "-crf", "23", "-c:a", "aac",
                    out_path
                ]
                subprocess.run(fallback_cmd, capture_output=True)
                save_job(job_id, "video", status="completed", progress=100, result_url=f"/output/{out_filename}")
        except Exception as e:
            save_job(job_id, "video", status="failed", error=str(e))

    import threading
    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": "Edição de vídeo viral iniciada em segundo plano.", "cost": 10}

# ----------------------------------------------------------------------------------------
# 7. STRIPE CHECKOUT (SISTEMA PRÉ-PAGO)
# ----------------------------------------------------------------------------------------
PACKAGES = {
    "starter": {"name": "Pacote Starter (100 Créditos)", "credits": 100, "price_brl": 29.90, "cents": 2990},
    "pro": {"name": "Pacote Pro (250 Créditos)", "credits": 250, "price_brl": 59.90, "cents": 5990},
    "viral": {"name": "Pacote Viral Agency (700 Créditos)", "credits": 700, "price_brl": 129.90, "cents": 12990}
}

@app.post("/api/stripe/create-checkout")
async def create_checkout_session(
    package_id: str = Form(...),
    user_id: str = Form("default_user")
):
    pkg = PACKAGES.get(package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Pacote inválido")

    if not STRIPE_SECRET_KEY:
        # Modo simulação local para testes imediatos sem chave configurada
        add_credits(user_id, pkg['credits'])
        return {
            "mode": "test_auto_recharge",
            "message": f"Créditos recarregados em modo teste (+{pkg['credits']} créditos).",
            "new_balance": get_user_credits(user_id)
        }

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.create(
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': f"IABOX — {pkg['name']}",
                        'description': f"Recarga pré-paga de {pkg['credits']} créditos para criação de vídeos, áudios e músicas na plataforma IABOX.",
                    },
                    'unit_amount': pkg['cents'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"https://iabox.evandrosilvagallina.cloud/?payment=success&credits={pkg['credits']}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"https://iabox.evandrosilvagallina.cloud/?payment=cancel",
            metadata={'user_id': user_id, 'credits': str(pkg['credits'])}
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stripe/verify-session")
def verify_stripe_session(session_id: str, user_id: str = "default_user"):
    if not STRIPE_SECRET_KEY:
        return {"status": "mock_success", "credits_added": 100}
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id FROM orders WHERE stripe_session_id = ?", (session_id,))
            already_processed = c.fetchone()
            if not already_processed:
                credits_to_add = int(session.metadata.get("credits", 100))
                c.execute("INSERT INTO orders (id, user_id, amount_brl, credits, status, stripe_session_id) VALUES (?, ?, ?, ?, ?, ?)",
                          (str(uuid.uuid4()), user_id, session.amount_total / 100.0, credits_to_add, "paid", session_id))
                c.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (credits_to_add, user_id))
                conn.commit()
                conn.close()
                return {"status": "success", "credits_added": credits_to_add, "new_balance": get_user_credits(user_id)}
            conn.close()
            return {"status": "already_credited", "new_balance": get_user_credits(user_id)}
        else:
            return {"status": "pending", "payment_status": session.payment_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    # Processa evento de confirmação de pagamento
    try:
        event = json.loads(payload)
        if event.get("type") == "checkout.session.completed":
            session = event['data']['object']
            user_id = session.get('metadata', {}).get('user_id', 'default_user')
            credits_to_add = int(session.get('metadata', {}).get('credits', 100))
            add_credits(user_id, credits_to_add)
            print(f"[Stripe Webhook] Recarga confirmada: +{credits_to_add} créditos para {user_id}")
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
