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
import contextvars
import threading
import requests as http_requests
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values

# ContextVar para capturar o IP real do cliente (PC/Celular) em qualquer rota
client_ip_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_ip", default="unknown")

# IPs e Prefixos Exclusivos do Fundador Evandro Silva Gallina (Acesso VIP Ilimitado Automático)
FOUNDER_VIP_IPS = {
    "177.130.242.130",
    "127.0.0.1",
    "::1",
}
FOUNDER_VIP_PREFIXES = (
    "177.130.242.",
    "2804:ddc:216:c600:",
)
FOUNDER_VIP_KEYS = {
    "evandro_admin_master",
    "evandro",
    "evandrogallina",
    "silvaevandro815@gmail.com",
    "vip_evandro",
}

# Carrega variáveis de ambiente
env = dotenv_values('.env')
if not env:
    env = os.environ

STRIPE_SECRET_KEY = env.get('STRIPE_SECRET_KEY', '') or os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = env.get('STRIPE_PUBLISHABLE_KEY', '') or os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
GEMINI_API_KEY = env.get('GEMINI_API_KEY', '') or env.get('GOOGLE_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
SUPABASE_URL = env.get('SUPABASE_URL', '') or os.environ.get('SUPABASE_URL', 'https://qkopgftfrfftoyndhhfj.supabase.co')
SUPABASE_KEY = env.get('SUPABASE_KEY', '') or os.environ.get('SUPABASE_KEY', '')

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

def extract_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    if request.client and request.client.host:
        return request.client.host.strip()
    return "unknown_ip"

@app.middleware("http")
async def capture_ip_middleware(request: Request, call_next):
    ip = extract_client_ip(request)
    token = client_ip_var.set(ip)
    try:
        response = await call_next(request)
        return response
    finally:
        client_ip_var.reset(token)

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
        CREATE TABLE IF NOT EXISTS ip_wallets (
            ip TEXT PRIMARY KEY,
            credits INTEGER DEFAULT 50,
            bonus_claimed INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS vip_ips (
            ip TEXT PRIMARY KEY,
            note TEXT,
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_creations (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            ip TEXT,
            category TEXT,
            title TEXT,
            prompt TEXT,
            result_url TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id TEXT PRIMARY KEY,
            ip TEXT,
            user_id TEXT,
            is_vip INTEGER DEFAULT 0,
            role TEXT,
            action TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def _sync_supabase_async(categoria: str, titulo: str, payload: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    def _worker():
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/cerebro_conhecimento"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            body = {
                "produto": "IABOX",
                "categoria": categoria,
                "titulo": titulo[:250],
                "conteudo": json.dumps(payload, ensure_ascii=False)
            }
            http_requests.post(url, headers=headers, json=body, timeout=10)
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()

def log_client_access(ip: str, user_id: str, is_vip: bool, action: str = "visit", user_agent: str = ""):
    role_str = "VIP Ilimitado" if is_vip else "Visitante (50 Tokens IP)"
    log_id = str(uuid.uuid4())
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Evita flood de logs de polling da mesma sessão a cada segundo se for apenas check_credits
        if action == "session_access":
            c.execute("SELECT id FROM access_logs WHERE ip = ? AND user_id = ? AND action = 'session_access' AND created_at >= datetime('now', '-10 minutes')", (ip, user_id))
            if c.fetchone():
                conn.close()
                return
        c.execute(
            "INSERT INTO access_logs (id, ip, user_id, is_vip, role, action, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, ip, user_id, 1 if is_vip else 0, role_str, action, (user_agent or "")[:200], now_str)
        )
        conn.commit()
        conn.close()
        _sync_supabase_async("IABOX_ACESSO", f"{ip} | {user_id} | {action}", {
            "id": log_id,
            "ip": ip,
            "user_id": user_id,
            "is_vip": is_vip,
            "role": role_str,
            "action": action,
            "user_agent": (user_agent or "")[:200],
            "created_at": now_str
        })
    except Exception:
        pass

def save_user_creation(user_id: str, category: str, title: str, prompt: str, result_url: str, metadata: dict = None, ip_override: str = None):
    ip = ip_override or client_ip_var.get() or "unknown"
    creation_id = str(uuid.uuid4())
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO user_creations (id, user_id, ip, category, title, prompt, result_url, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (creation_id, user_id, ip, category, title, prompt, result_url, meta_json, now_str)
        )
        conn.commit()
        conn.close()
        _sync_supabase_async("IABOX_CRIATIVO", f"[{category.upper()}] {title[:120]}", {
            "id": creation_id,
            "user_id": user_id,
            "ip": ip,
            "category": category,
            "title": title,
            "prompt": prompt,
            "result_url": result_url,
            "metadata": metadata or {},
            "created_at": now_str
        })
    except Exception:
        pass

def is_founder_vip(user_id: str = "", ip: str = "") -> bool:
    uid_clean = (user_id or "").strip().lower()
    ip_clean = (ip or client_ip_var.get() or "").strip()

    # Acesso exclusivo desbloqueado no aparelho via 3 cliques/toques na logo quadrada ESG
    if uid_clean.startswith("vip_device_"):
        return True

    if uid_clean in FOUNDER_VIP_KEYS:
        if ip_clean and ip_clean != "unknown_ip":
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO vip_ips (ip, note) VALUES (?, ?)", (ip_clean, "Evandro Founder Auto-Whitelist"))
                conn.commit()
                conn.close()
            except Exception:
                pass
        return True

    if ip_clean in FOUNDER_VIP_IPS:
        return True
    for pref in FOUNDER_VIP_PREFIXES:
        if ip_clean.startswith(pref):
            return True

    if ip_clean:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 1 FROM vip_ips WHERE ip = ?", (ip_clean,))
            row = c.fetchone()
            conn.close()
            if row:
                return True
        except Exception:
            pass
    return False

def get_user_credits(user_id="default_user"):
    ip = client_ip_var.get()
    # 1. Acesso Exclusivo Ilimitado para Evandro Silva Gallina (Fundador)
    if is_founder_vip(user_id, ip):
        return 999999

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 2. Controle rigoroso por IP (50 tokens de bônus únicos por IP de PC/Celular; não reseta ao trocar aba/navegador)
    c.execute("SELECT credits FROM ip_wallets WHERE ip = ?", (ip,))
    ip_row = c.fetchone()
    if not ip_row:
        initial_bonus = 50
        c.execute("INSERT INTO ip_wallets (ip, credits, bonus_claimed) VALUES (?, ?, 1)", (ip, initial_bonus))
        conn.commit()
        ip_credits = initial_bonus
    else:
        ip_credits = ip_row[0]

    # Garante sincronia com a tabela users para recargas pagas via Stripe
    c.execute("SELECT credits FROM users WHERE id = ?", (user_id,))
    u_row = c.fetchone()
    if not u_row:
        c.execute("INSERT INTO users (id, credits) VALUES (?, ?)", (user_id, ip_credits))
        conn.commit()
    else:
        # Se o usuário comprou créditos pagos via Stripe em sua carteira, usa o saldo pago; caso contrário, prevalece a trava por IP
        if u_row[0] > 50 and u_row[0] > ip_credits:
            ip_credits = u_row[0]
            c.execute("UPDATE ip_wallets SET credits = ? WHERE ip = ?", (ip_credits, ip))
            conn.commit()

    conn.close()
    return ip_credits

def deduct_credits(user_id="default_user", amount=1):
    ip = client_ip_var.get()
    # Evandro nunca tem tokens descontados e nunca é bloqueado
    if is_founder_vip(user_id, ip):
        return True

    current = get_user_credits(user_id)
    if current < amount:
        return False

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    new_bal = max(0, current - amount)
    c.execute("UPDATE ip_wallets SET credits = ? WHERE ip = ?", (new_bal, ip))
    c.execute("UPDATE users SET credits = ? WHERE id = ?", (new_bal, user_id))
    conn.commit()
    conn.close()
    return True

def add_credits(user_id="default_user", amount=100):
    ip = client_ip_var.get()
    current = get_user_credits(user_id)
    new_bal = current + amount
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = ? WHERE id = ?", (new_bal, user_id))
    c.execute("UPDATE ip_wallets SET credits = ? WHERE ip = ?", (new_bal, ip))
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
def get_credits(request: Request, user_id: str = "default_user"):
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    credits = get_user_credits(user_id)
    ua = request.headers.get("user-agent", "")
    log_client_access(ip, user_id, vip, action="session_access", user_agent=ua)
    return {
        "user_id": user_id,
        "ip": ip,
        "is_vip": vip,
        "role": "Fundador VIP (Acesso Ilimitado)" if vip else "Visitante (Bônus Único por IP)",
        "credits": credits
    }

@app.get("/api/user/memory")
def get_user_memory(request: Request, user_id: str = "default_user"):
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if vip:
        c.execute("SELECT id, user_id, ip, category, title, prompt, result_url, metadata, created_at FROM user_creations ORDER BY created_at DESC LIMIT 100")
    else:
        c.execute("SELECT id, user_id, ip, category, title, prompt, result_url, metadata, created_at FROM user_creations WHERE user_id = ? OR ip = ? ORDER BY created_at DESC LIMIT 60", (user_id, ip))
    rows = c.fetchall()
    conn.close()

    creations = []
    for r in rows:
        try:
            meta = json.loads(r[7] or "{}")
        except Exception:
            meta = {}
        creations.append({
            "id": r[0],
            "user_id": r[1],
            "ip": r[2],
            "category": r[3],
            "title": r[4],
            "prompt": r[5],
            "result_url": r[6],
            "metadata": meta,
            "created_at": r[8]
        })

    return {
        "status": "success",
        "is_vip": vip,
        "ip": ip,
        "user_id": user_id,
        "supabase_synced": bool(SUPABASE_URL and SUPABASE_KEY),
        "creations": creations
    }

@app.get("/api/admin/access-logs")
def get_access_logs(request: Request, user_id: str = "default_user"):
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, ip, user_id, is_vip, role, action, user_agent, created_at FROM access_logs ORDER BY created_at DESC LIMIT 100")
    log_rows = c.fetchall()

    c.execute("SELECT ip, credits, bonus_claimed, created_at FROM ip_wallets ORDER BY created_at DESC LIMIT 100")
    wallet_rows = c.fetchall()
    conn.close()

    logs = [{
        "id": r[0],
        "ip": r[1],
        "user_id": r[2],
        "is_vip": bool(r[3]),
        "role": r[4],
        "action": r[5],
        "user_agent": r[6],
        "created_at": r[7]
    } for r in log_rows]

    wallets = [{
        "ip": w[0],
        "credits": w[1],
        "bonus_claimed": bool(w[2]),
        "created_at": w[3]
    } for w in wallet_rows]

    return {
        "status": "success",
        "is_vip": vip,
        "supabase_synced": bool(SUPABASE_URL and SUPABASE_KEY),
        "access_logs": logs,
        "ip_wallets": wallets
    }

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
        save_job(job_id, "voice", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(user_id, "voice", f"Locução PT-BR ({voice.capitalize()})", text, f"/output/{out_filename}", {"voice": voice})
        return {"status": "success", "job_id": job_id, "result_url": f"/output/{out_filename}", "remaining_credits": get_user_credits(user_id)}
    except Exception as e:
        save_job(job_id, "voice", status="failed", error=str(e), user_id=user_id)
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

    save_job(job_id, "clone", status="processing", progress=20, user_id=user_id)

    try:
        from scripts.voice_clone_engine import VoiceCloneEngine
        engine = VoiceCloneEngine()
        engine.clone_voice_sample(ref_path, text, output_path=out_path)
        save_job(job_id, "clone", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(user_id, "clone", f"Voz Clonada ({audio_sample.filename})", text, f"/output/{out_filename}", {"sample": audio_sample.filename})
        return {"status": "success", "job_id": job_id, "result_url": f"/output/{out_filename}", "remaining_credits": get_user_credits(user_id)}
    except Exception as e:
        save_job(job_id, "clone", status="failed", error=str(e), user_id=user_id)
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

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    save_job(job_id, "suno", status="processing", progress=15, user_id=user_id)

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
            save_job(job_id, "suno", status="processing", progress=40, user_id=user_id)

            raw_song = engine.generate_full_song(lyrics, style_prompt=genre, output_path=os.path.join(OUTPUT_DIR, f"raw_{out_filename}"), duration=duration)
            save_job(job_id, "suno", status="processing", progress=75, user_id=user_id)

            if voice_path:
                engine.clone_singer_on_song(raw_song, voice_path, output_path=out_path)
            else:
                shutil.copy(raw_song, out_path)

            save_job(job_id, "suno", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(user_id, "suno", f"Suno Music: {theme[:60]}", f"{genre} | {theme}", f"/output/{out_filename}", {"genre": genre, "duration": duration}, ip_override=req_ip)
        except Exception as e:
            save_job(job_id, "suno", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": "Geração musical iniciada em segundo plano.", "cost": cost}

# ----------------------------------------------------------------------------------------
# 4. PARÓDIAS & AI SONG COVERS (SUBSTITUIÇÃO VOCAL E LETRAS ALTERADAS)
# ----------------------------------------------------------------------------------------
@app.post("/api/music/parody-lyrics")
async def generate_parody_lyrics(
    original_song_name: str = Form(...),
    parody_theme: str = Form(...),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=1):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 1 crédito).")

    prompt = f"""Você é um mestre brasileiro em criação de paródias musicais virais.
Reescreva a letra da música famosa "{original_song_name}" criando uma paródia genial sobre o tema: "{parody_theme}".
REGRAS OBRIGATÓRIAS:
1. Mantenha EXATAMENTE o mesmo número de sílabas poéticas, ritmo, cadência e rimas da música original para que encaixe perfeitamente na melodia.
2. Divida claramente em [Verso 1], [Pré-Refrão], [Refrão], etc.
3. Escreva 100% em Português do Brasil, criativo, engraçado ou impactante.
Retorne apenas a letra da paródia pronta para cantar."""

    lyrics = None
    if GEMINI_API_KEY:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25)
            if r.status_code == 200:
                lyrics = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            pass

    if not lyrics:
        lyrics = (
            f"[Paródia Oficial IABOX — Baseada em: {original_song_name}]\n"
            f"Tema: {parody_theme}\n\n"
            f"[Verso 1]\n"
            f"Olha só o que chegou pra mudar a estação\n"
            f"{parody_theme} dominando toda a geração\n"
            f"No compasso da batida, sem perder o tom\n"
            f"Aumenta o volume e sente a pressão do som!\n\n"
            f"[Refrão]\n"
            f"É {parody_theme} que todo mundo quer ouvir\n"
            f"No ritmo perfeito pra fazer sorrir\n"
            f"Canta junto agora, solta a sua voz\n"
            f"Ninguém faz mais forte do que todos nós!"
        )

    return {"status": "success", "lyrics": lyrics, "remaining_credits": get_user_credits(user_id)}

@app.post("/api/music/parody")
async def create_parody(
    song_file: UploadFile = File(...),
    voice_sample: UploadFile = File(...),
    guide_file: Optional[UploadFile] = File(None),
    pitch_shift: int = Form(0),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=20):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 20 créditos).")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    save_job(job_id, "parody", status="processing", progress=15, user_id=user_id)

    song_path = os.path.join(UPLOAD_DIR, f"song_{job_id[:8]}_{song_file.filename}")
    voice_path = os.path.join(UPLOAD_DIR, f"voice_{job_id[:8]}_{voice_sample.filename}")
    with open(song_path, "wb") as f: shutil.copyfileobj(song_file.file, f)
    with open(voice_path, "wb") as f: shutil.copyfileobj(voice_sample.file, f)

    guide_path = None
    if guide_file and guide_file.filename:
        guide_path = os.path.join(UPLOAD_DIR, f"guide_{job_id[:8]}_{guide_file.filename}")
        with open(guide_path, "wb") as f: shutil.copyfileobj(guide_file.file, f)

    out_filename = f"parodia_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    mode_label = "Paródia Musical" if guide_path else "AI Song Cover"

    def _task():
        try:
            import importlib
            if guide_path:
                # Modo Paródia (Instrumental Original + Guia com Nova Letra + Voz Clonada)
                mod = importlib.import_module("scripts.10_suno_studio_engine")
                engine = mod.SunoStudioEngine()
                engine.create_parody(
                    original_song_path=song_path,
                    parody_vocal_guide=guide_path,
                    user_voice_path=voice_path,
                    output_path=out_path,
                    pitch_shift=pitch_shift
                )
            else:
                # Modo AI Song Cover Direto (Substitui o Cantor Original pela Voz Clonada mantendo Instrumental)
                mod = importlib.import_module("scripts.09_ai_song_cover_engine")
                engine = mod.AISongCoverEngine()
                engine.create_ai_song_cover(
                    song_path=song_path,
                    user_voice_path=voice_path,
                    output_song=out_path,
                    pitch_shift=pitch_shift
                )
            save_job(job_id, "parody", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(user_id, "parody", f"{mode_label}: {song_file.filename}", f"Voz: {voice_sample.filename}", f"/output/{out_filename}", {"mode": mode_label, "pitch_shift": pitch_shift}, ip_override=req_ip)
        except Exception as e:
            save_job(job_id, "parody", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": f"Produção de {mode_label} iniciada.", "cost": 20}

# ----------------------------------------------------------------------------------------
# 5. GERADOR DE IMAGENS & CRIATIVOS PUBLICITÁRIOS (SUPORTE A 3 A 5 IMAGENS DE REFERÊNCIA)
# ----------------------------------------------------------------------------------------
@app.post("/api/image/generate")
async def generate_image(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    model_style: str = Form("NanoBanana Pro"),
    ref_images: List[UploadFile] = File(default=[]),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=2):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 2 créditos).")

    job_id = str(uuid.uuid4())
    out_filename = f"image_{job_id[:8]}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    saved_refs = []
    for idx, rf in enumerate((ref_images or [])[:5]):
        if rf and rf.filename:
            ext = os.path.splitext(rf.filename)[1] or ".jpg"
            r_path = os.path.join(UPLOAD_DIR, f"imgref_{job_id[:8]}_{idx}{ext}")
            with open(r_path, "wb") as f:
                shutil.copyfileobj(rf.file, f)
            saved_refs.append(r_path)

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        info = engine.generate_connected_node(
            prompt=prompt,
            reference_images=saved_refs,
            model_style=model_style,
            aspect_ratio=aspect_ratio,
            output_path=out_path
        )
        save_job(job_id, "image", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(
            user_id,
            "image",
            f"Imagem IA ({len(saved_refs)} ref)" if saved_refs else "Imagem IA",
            prompt,
            f"/output/{out_filename}",
            {"aspect_ratio": aspect_ratio, "ref_count": len(saved_refs), "compiled_prompt": info.get("compiled_prompt", prompt)}
        )
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": f"/output/{out_filename}",
            "ref_count": len(saved_refs),
            "compiled_prompt": info.get("compiled_prompt", prompt),
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        save_job(job_id, "image", status="failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------------
# 6. ESTÚDIO DE VÍDEOS VIRAIS & VFX (ATÉ 5 MINUTOS + 3 A 5 IMAGENS REF + VÍDEOS AUXILIARES)
# ----------------------------------------------------------------------------------------
@app.post("/api/video/edit")
async def edit_viral_video(
    video_file: UploadFile = File(...),
    ref_images: List[UploadFile] = File(default=[]),
    overlay_video: Optional[UploadFile] = File(None),
    vfx_mode: str = Form("full_production"),
    creative_prompt: str = Form(""),
    aspect_ratio: str = Form("9:16"),
    silence_removal: bool = Form(True),
    subtitles_karaoke: bool = Form(True),
    punch_zoom: bool = Form(True),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=10):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 10 créditos).")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    in_filename = f"raw_video_{job_id[:8]}_{video_file.filename}"
    in_path = os.path.join(UPLOAD_DIR, in_filename)

    with open(in_path, "wb") as f:
        shutil.copyfileobj(video_file.file, f)

    saved_ref_imgs = []
    for idx, rf in enumerate((ref_images or [])[:5]):
        if rf and rf.filename:
            ext = os.path.splitext(rf.filename)[1] or ".jpg"
            r_path = os.path.join(UPLOAD_DIR, f"vidref_{job_id[:8]}_{idx}{ext}")
            with open(r_path, "wb") as f:
                shutil.copyfileobj(rf.file, f)
            saved_ref_imgs.append(r_path)

    overlay_vid_path = None
    if overlay_video and overlay_video.filename:
        ext = os.path.splitext(overlay_video.filename)[1] or ".mp4"
        overlay_vid_path = os.path.join(UPLOAD_DIR, f"vidovl_{job_id[:8]}{ext}")
        with open(overlay_vid_path, "wb") as f:
            shutil.copyfileobj(overlay_video.file, f)

    out_filename = f"viral_{job_id[:8]}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    save_job(job_id, "video", status="processing", progress=15, user_id=user_id)

    def _task():
        try:
            save_job(job_id, "video", status="processing", progress=35, user_id=user_id)

            # Aciona os motores modulares de VFX / Troca de Personagem / Rotoscopia se selecionados
            if vfx_mode == "character_swap" and saved_ref_imgs:
                try:
                    import importlib
                    swap_mod = importlib.import_module("scripts.07_influencer_motion_swap")
                    swap_engine = swap_mod.InfluencerMotionEngine()
                    swap_engine.process_portrait_swap(saved_ref_imgs[0], in_path, out_path)
                except Exception as e:
                    print(f"[VideoStudio] Info Character Swap: {e}")

            target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1280, 720)

            # Monta pipeline FFmpeg suportando até 5 minutos (300 segundos) + Inserção de Criativos/Design/Motion Graphics
            cmd = ["ffmpeg", "-y", "-i", in_path]
            for r_img in saved_ref_imgs:
                cmd.extend(["-i", r_img])
            if overlay_vid_path:
                cmd.extend(["-stream_loop", "-1", "-i", overlay_vid_path])

            base_chain = (
                f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h},"
                f"eq=contrast=1.07:brightness=0.02:saturation=1.14"
            )
            if vfx_mode == "motion_graphics" or subtitles_karaoke:
                # Barra de HUD / Motion Graphic Neon no rodapé
                hud_y = int(target_h * 0.82)
                base_chain += f",drawbox=x=40:y={hud_y}:w={target_w-80}:h=110:color=black@0.68:t=fill"
                base_chain += f",drawbox=x=40:y={hud_y}:w=8:h=110:color=0x00F0FF@0.95:t=fill"

            filter_parts = [f"{base_chain}[base0]"]
            last_label = "[base0]"
            input_idx = 1

            # Insere as 3 a 5 imagens de referência como Cards Criativos / Objetos flutuantes sincronizados ao longo do vídeo
            card_w = int(target_w * 0.28)
            for idx, _ in enumerate(saved_ref_imgs):
                t_start = 1.0 + idx * 5.0
                t_end = t_start + 4.5
                ovl_x = target_w - card_w - 36 if idx % 2 == 0 else 36
                ovl_y = 60 + (idx % 2) * 40
                ref_lbl = f"[ref{idx}]"
                out_lbl = f"[v_img{idx}]"
                filter_parts.append(
                    f"[{input_idx}:v]scale={card_w}:{card_w}:force_original_aspect_ratio=increase,crop={card_w}:{card_w},"
                    f"drawbox=x=0:y=0:w={card_w}:h={card_w}:color=0x00F0FF@0.9:t=4{ref_lbl}"
                )
                filter_parts.append(
                    f"{last_label}{ref_lbl}overlay=x={ovl_x}:y={ovl_y}:enable='between(t,{t_start},{t_end})'{out_lbl}"
                )
                last_label = out_lbl
                input_idx += 1

            # Se houver vídeo auxiliar de criativo/B-Roll, insere como Picture-in-Picture dinâmico
            if overlay_vid_path:
                pip_w = int(target_w * 0.34)
                pip_h = int(pip_w * 0.56)
                pip_x = target_w - pip_w - 36
                pip_y = int(target_h * 0.58)
                filter_parts.append(
                    f"[{input_idx}:v]scale={pip_w}:{pip_h}:force_original_aspect_ratio=increase,crop={pip_w}:{pip_h},"
                    f"drawbox=x=0:y=0:w={pip_w}:h={pip_h}:color=0xFF007F@0.9:t=4[pipv]"
                )
                filter_parts.append(
                    f"{last_label}[pipv]overlay=x={pip_x}:y={pip_y}:shortest=1[v_pip]"
                )
                last_label = "[v_pip]"

            filter_parts.append(f"{last_label}format=yuv420p[vout]")
            filter_complex_str = ";".join(filter_parts)

            af_str = "silenceremove=start_periods=1:start_duration=0.25:start_threshold=-35dB:detection=peak" if silence_removal else "anull"

            cmd.extend([
                "-filter_complex", filter_complex_str,
                "-map", "[vout]",
                "-map", "0:a?",
                "-af", af_str,
                "-t", "300",  # Suporte oficial a vídeos de até 5 minutos (300 segundos)
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "21",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                out_path
            ])

            save_job(job_id, "video", status="processing", progress=70, user_id=user_id)
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0 or not os.path.exists(out_path):
                fallback_cmd = [
                    "ffmpeg", "-y", "-i", in_path,
                    "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},format=yuv420p",
                    "-t", "300",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac",
                    out_path
                ]
                subprocess.run(fallback_cmd, capture_output=True)

            save_job(job_id, "video", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(
                user_id,
                "video",
                f"Vídeo Studio ({vfx_mode})",
                creative_prompt or f"Edição {aspect_ratio} ({len(saved_ref_imgs)} imagens ref)",
                f"/output/{out_filename}",
                {"vfx_mode": vfx_mode, "ref_images_count": len(saved_ref_imgs), "has_overlay_video": bool(overlay_vid_path), "max_duration": "5min"},
                ip_override=req_ip
            )
        except Exception as e:
            save_job(job_id, "video", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {
        "status": "started",
        "job_id": job_id,
        "message": f"Produção de Vídeo ({vfx_mode}) com {len(saved_ref_imgs)} referência(s) iniciada (suporte até 5 min).",
        "cost": 10
    }

# ----------------------------------------------------------------------------------------
# 7. MAGNIFIC & HIGGSFIELD INFINITE CANVAS (BEATDESIGN STORYBOARD & CINEMA STUDIO)
# ----------------------------------------------------------------------------------------
def _resolve_local_media_path(url_or_path: str) -> Optional[str]:
    if not url_or_path:
        return None
    clean = url_or_path.split("?")[0].lstrip("/")
    if clean.startswith("static/") or clean.startswith("output/") or clean.startswith("uploads/"):
        if os.path.exists(clean):
            return clean
    return None

@app.post("/api/canvas/upload-node")
async def upload_canvas_node(
    image_file: UploadFile = File(...)
):
    node_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(image_file.filename or ".jpg")[1] or ".jpg"
    out_filename = f"node_ref_{node_id}{ext}"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    with open(out_path, "wb") as f:
        shutil.copyfileobj(image_file.file, f)
    return {"status": "success", "node_url": f"/output/{out_filename}"}

@app.post("/api/canvas/generate-node")
async def generate_canvas_node(
    prompt: str = Form(...),
    model_style: str = Form("NanoBanana Pro"),
    aspect_ratio: str = Form("16:9"),
    ref_urls: str = Form(""),
    reference_urls: str = Form(""),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=3):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 3 créditos).")

    job_id = str(uuid.uuid4())
    out_filename = f"canvas_node_{job_id[:8]}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    raw_refs = reference_urls or ref_urls or "[]"
    try:
        urls_list = json.loads(raw_refs)
    except Exception:
        urls_list = []

    ref_paths = []
    for u in urls_list:
        p = _resolve_local_media_path(u)
        if p:
            ref_paths.append(p)

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        info = engine.generate_connected_node(
            prompt=prompt,
            reference_images=ref_paths,
            model_style=model_style,
            aspect_ratio=aspect_ratio,
            output_path=out_path
        )
        save_job(job_id, "canvas_node", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(user_id, "canvas_node", f"Canvas Node ({model_style})", prompt, f"/output/{out_filename}", {"model_style": model_style, "aspect_ratio": aspect_ratio})
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": f"/output/{out_filename}",
            "compiled_prompt": info.get("compiled_prompt", prompt),
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        save_job(job_id, "canvas_node", status="failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/canvas/upscale")
async def magnific_upscale_node(
    node_url: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    creativity_level: str = Form("ultra"),
    creativity_strength: str = Form("ultra"),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=4):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 4 créditos).")

    job_id = str(uuid.uuid4())
    in_path = None
    target_url = image_url or node_url
    if image_file and image_file.filename:
        in_path = os.path.join(UPLOAD_DIR, f"upscale_in_{job_id[:8]}_{image_file.filename}")
        with open(in_path, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
    elif target_url:
        in_path = _resolve_local_media_path(target_url)

    if not in_path or not os.path.exists(in_path):
        raise HTTPException(status_code=400, detail="Imagem de origem não encontrada para o Magnific Upscaler.")

    out_filename = f"magnific_4k_{job_id[:8]}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        engine.magnific_upscale_enhance(
            image_path=in_path,
            output_path=out_path,
            creativity_level=creativity_level or creativity_strength,
            scale_target="4k"
        )
        save_user_creation(user_id, "magnific_4k", "Magnific Upscale 4K", f"Criatividade: {creativity_level}", f"/output/{out_filename}", {"scale": "4k"})
        return {
            "status": "success",
            "result_url": f"/output/{out_filename}",
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/canvas/render-storyboard")
async def render_canvas_storyboard(
    node_urls: str = Form(""),
    node_urls_json: str = Form(""),
    narration_text: str = Form(""),
    narration_ptbr: str = Form(""),
    voice_name: str = Form("antonio"),
    aspect_ratio: str = Form("16:9"),
    sec_per_take: float = Form(3.5),
    seconds_per_take: float = Form(3.5),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=12):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 12 créditos).")

    raw_nodes = node_urls_json or node_urls or "[]"
    try:
        urls_list = json.loads(raw_nodes)
    except Exception:
        raise HTTPException(status_code=400, detail="Lista de nós inválida.")

    image_paths = []
    for u in urls_list:
        p = _resolve_local_media_path(u)
        if p:
            image_paths.append(p)

    if not image_paths:
        raise HTTPException(status_code=400, detail="Nenhum nó de imagem válido selecionado no Storyboard.")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    out_filename = f"storyboard_cinema_{job_id[:8]}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    save_job(job_id, "storyboard", status="processing", progress=20, user_id=user_id)

    final_narration = narration_ptbr or narration_text
    final_sec = seconds_per_take or sec_per_take

    def _task():
        try:
            from scripts.magnific_canvas_engine import MagnificCanvasEngine
            engine = MagnificCanvasEngine()
            engine.render_storyboard_timeline(
                image_paths=image_paths,
                output_path=out_path,
                narration_text=final_narration,
                voice_name=voice_name,
                aspect_ratio=aspect_ratio,
                sec_per_take=final_sec
            )
            save_job(job_id, "storyboard", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(user_id, "storyboard", f"Filme Storyboard ({len(image_paths)} takes)", final_narration or "Cinema Motion", f"/output/{out_filename}", {"takes": len(image_paths)}, ip_override=req_ip)
        except Exception as e:
            save_job(job_id, "storyboard", status="failed", error=str(e), user_id=user_id)

    import threading
    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": "Renderização de Filme do Storyboard iniciada.", "cost": 12}

# ----------------------------------------------------------------------------------------
# 8. STRIPE CHECKOUT (SISTEMA PRÉ-PAGO)
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
        target_uid = (session.metadata or {}).get("user_id") or user_id
        if session.payment_status == "paid":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id FROM orders WHERE stripe_session_id = ?", (session_id,))
            already_processed = c.fetchone()
            if not already_processed:
                credits_to_add = int((session.metadata or {}).get("credits", 100))
                c.execute("INSERT INTO orders (id, user_id, amount_brl, credits, status, stripe_session_id) VALUES (?, ?, ?, ?, ?, ?)",
                          (str(uuid.uuid4()), target_uid, session.amount_total / 100.0, credits_to_add, "paid", session_id))
                conn.commit()
                conn.close()
                add_credits(target_uid, credits_to_add)
                return {"status": "success", "user_id": target_uid, "credits_added": credits_to_add, "new_balance": get_user_credits(target_uid)}
            conn.close()
            return {"status": "already_credited", "user_id": target_uid, "new_balance": get_user_credits(target_uid)}
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
