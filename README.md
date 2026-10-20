# ⚡ IABOX — Plataforma e Estúdio de IA

> **Domínio de Produção:** [https://iabox.evandrosilvagallina.cloud](https://iabox.evandrosilvagallina.cloud)  
> **Fundador & Arquiteto:** Evandro Silva Gallina  
> **Infraestrutura:** VPS KVM 4 Hostinger + Coolify (Docker PaaS)

---

## 🚀 Sobre o Projeto

O **IABOX** é o ecossistema tudo-em-um para geração de criativos audiovisuais, músicas e vozes brasileiras de alta performance:

1. **🎬 Editor de Vídeos Virais (Reels/Shorts 9:16):** Detecção e corte inteligente de silêncios (jump cuts), legendas dinâmicas estilo Hormozi, punch-in zoom e stickers animados.
2. **🎙️ Locuções Neurais 100% Brasil (PT-BR):** Síntese neural masculina e feminina sem nenhum sotaque estrangeiro (Antonio, Francisca, Thalita).
3. **🧬 Clonador de Voz Instantâneo (1 Minuto):** Mapeamento do trato vocal a partir de 60 segundos de áudio de referência para narrar qualquer novo texto.
4. **🎵 Suno Studio (Músicas Inéditas do Zero):** Criação de canções completas (vocais + instrumental) a partir de um prompt em qualquer gênero musical (Sertanejo, Funk, Trap, Rock, Pop) com a sua voz cantando.
5. **🎭 Fábrica de Paródias & AI Covers:** Separação de stems com Demucs v4 (Meta AI), preservando o instrumental de canções famosas e substituindo a letra cantada com a sua voz clonada afinada via Seed-VC (F0 pitch tracking).
6. **🤖 Mascote IABot Interativo:** Mascote flutuante dinâmico e arrastável por mouse ou touch em smartphones e tablets.
7. **💳 Sistema Pré-Pago Pay-as-you-go:** Integração com Stripe e PIX com consumo de saldo por créditos.

---

## 🛠️ Stack Tecnológica

- **Backend:** FastAPI (Python 3.12), SQLite, Uvicorn, FFmpeg 7.1.
- **Frontend:** HTML5, Tailwind CSS, Lucide Icons, Glassmorphism, PointerEvents Touch API (Mobile, iPhone, iPad, PC).
- **Motores de IA:** Edge-TTS Neural PT-BR, Seed-VC (Diffusion Transformers com F0), Demucs v4 (Meta AI), Gemini 3.5 Flash / DiffRhythm.
- **Deploy:** Docker, Docker Compose, Coolify, Let's Encrypt (SSL HTTPS Automático).

---

## 🌐 Como Fazer o Deploy no Coolify (Hostinger VPS)

### Passo 1: No Painel do Coolify (`http://72.61.43.154:8000`)
1. Acesse o seu painel do Coolify.
2. Clique em **+ New Resource** &rarr; **Public Repository**.
3. Insira o link deste repositório:
   ```text
   https://github.com/silvaevandro815/iabox
   ```
4. Selecione o branch `main` e o tipo de build **Dockerfile** (ou **Docker Compose**).
5. No campo **Domains**, configure o seu domínio:
   ```text
   https://iabox.evandrosilvagallina.cloud
   ```
6. No campo **Port**, configure: `8000`.

### Passo 2: Variáveis de Ambiente no Coolify
Copie as variáveis do arquivo `.env`:
- `GEMINI_API_KEY`: Sua chave de IA do Google.
- `STRIPE_SECRET_KEY`: Sua chave secreta da Stripe.
- `STRIPE_PUBLISHABLE_KEY`: Sua chave pública da Stripe.

### Passo 3: Deploy com 1 Clique
- Clique em **Deploy** no Coolify.
- O Coolify construirá a imagem Docker, instalará o FFmpeg, subirá a aplicação e emitirá o certificado SSL HTTPS gratuitamente para `iabox.evandrosilvagallina.cloud`.

---

## 👤 Sobre o Criador

**Evandro Silva Gallina**  
*Especialista em Sistemas de IA, Gestão Pública e Comunicação Estratégica*  
- **Instagram:** [@evandrosilvagallina](https://instagram.com/evandrosilvagallina)  
- **LinkedIn:** [Evandro Silva Gallina](https://linkedin.com/in/evandro-sillva-gallina-83097b1aa)  
- **GitHub:** [@silvaevandro815](https://github.com/silvaevandro815)  
