
Claude finished the response
Let’s get cooking! Pick an artifact category or start building your idea from scratch.


Apps and websites

Documents and templates

Games

Productivity tools

Creative projects

Quiz or survey

Start from scratch

Edited 2 files, ran 2 commands, viewed a file
Edited 2 files, ran 2 commands, viewed a file
Hazır. esko-pwa.zip'i eskoredstar/ESKO GitHub reposuna yükleyin.

Yükledikten sonra önce şunu kontrol edin: https://esko-agent-gidj.onrender.com/health — "storage": "redis" görünüyorsa senkronizasyon kalıcı hale gelmiş demektir. Görünmüyorsa REDIS_URL environment variable'ı o servise de eklememiz gerekiyor.


Esko pwa
ZIP 
{"status":"ok","model":"claude-sonnet-4-6","key_configured":true,"sync":"active"}
"storage" alanı yok — bu eski kod çalışıyor, yeni agent_servisi.py deploy olmamış demek. Render'ın bağlı olduğu GitHub reposuna agent_servisi.py ve requirements.txt'i yüklemeniz gerekiyor.

Hangi GitHub reposuna bağladınız bu servisi? Render'da esko-agent-gidj servisine tıklayıp Settings sekmesinde görebilirsiniz.

https://github.com/EskoRedstar/esko-agent bu

Harika, o repoyu kontrol edeyim:


Fetched: GitHub - EskoRedstar/esko-agent
Fetched: GitHub - EskoRedstar/esko-agent
4 dosya repoda var — agent_servisi.py ve requirements.txt yüklenmiş. Render bu repoyu otomatik deploy etmeli, ama eski kodu çekmiş olabilir.

Render'da esko-agent-gidj servisine gidin → "Manual Deploy" → "Deploy latest commit" tıklayın. Deploy bittikten sonra https://esko-agent-gidj.onrender.com/health adresini açıp sonucu paylaşın — "storage": "redis" görünmeli.

{"status":"ok","model":"claude-sonnet-4-6","key_configured":true,"sync":"active"}
"storage" alanı hala yok — yeni kod deploy olmamış. Büyük ihtimalle repodaki agent_servisi.py eski versiyon. Kontrol edeyim:


Fetched: esko-agent/agent_servisi.py at main · EskoRedstar/esko-agent
Fetched: esko-agent/agent_servisi.py at main · EskoRedstar/esko-agent
Eski versiyon var — Redis kodu yok. Yeni agent_servisi.py'yi doğrudan GitHub'da güncelleyelim. Size dosyayı veriyorum, GitHub'da üzerine yazacaksınız:


Ran a command, read a file
Ran a command, read a file
Bu agent_servisi.py dosyasını indirip GitHub'daki EskoRedstar/esko-agent reposuna yükleyin — mevcut dosyanın üzerine yazın:

GitHub'da EskoRedstar/esko-agent reposuna gidin
agent_servisi.py dosyasına tıklayın
Sağ üstte kalem (edit) ikonuna tıklayın
Sayfanın üstünde "..." → "Upload file" seçin veya doğrudan az önce indirdiğiniz dosyayı sürükleyin
"Commit changes" tıklayın
Commit sonrası Render otomatik deploy edecek, birkaç dakika bekleyin, sonra /health adresini tekrar açın — "storage": "redis" görünmeli.


Agent servisi
PY 
Screenshot 2026-07-16 at 09.03.05.png
bulamadım ...

Düzenleme modunda açmışsınız — bu da iyi. Şimdi tüm içeriği seçip yenisiyle değiştirmeniz gerekiyor:

Ctrl+A (Mac'te Cmd+A) ile editördeki tüm metni seçin
Hepsini silin
Yeni agent_servisi.py dosyasının içeriğini yapıştırın
Dosyanın içeriğini kopyalamanız için hazırlıyorum:


Showing the new agent_servisi.py content to copy-paste into GitHub editor
Showing the new agent_servisi.py content to copy-paste into GitHub editor
GitHub'daki editörde:

Cmd+A ile tüm metni seçin
Silin
Aşağıdaki metni kopyalayıp yapıştırın:
python
"""
agent_servisi.py
=================
ESKO Analiz Asistanı + kalıcı cihazlar arası senkronizasyon (Redis).

Kurulum:
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn agent_servisi:app --reload --port 8001
"""

from __future__ import annotations

import os
import json
import logging
from typing import Optional, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agent_servisi")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
SYNC_KEY = os.environ.get("ESKO_SYNC_KEY", "esko-default")
REDIS_URL = os.environ.get("REDIS_URL", "")

app = FastAPI(title="ESKO Analiz Asistanı")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "PUT"],
    allow_headers=["*"],
)

_redis = None
_memory_store: dict = {}

async def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if not REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        await _redis.ping()
        log.info("Redis bağlantısı kuruldu.")
        return _redis
    except Exception as e:
        log.warning(f"Redis bağlanamadı: {e}")
        _redis = None
        return None

async def store_set(key: str, value: Any):
    r = await _get_redis()
    serialized = json.dumps(value, ensure_ascii=False)
    if r:
        await r.set(f"esko:{key}", serialized)
    else:
        _memory_store[key] = serialized

async def store_get(key: str) -> Any:
    r = await _get_redis()
    if r:
        val = await r.get(f"esko:{key}")
    else:
        val = _memory_store.get(key)
    return json.loads(val) if val else None

DEFAULT_SYSTEM_PROMPT = """Sen ESKO dashboard'unun finansal analiz asistanısın, Türkçe konuşursun.
VERİ KULLANIMI: Sana verilen güncel veriyi kullan, hafızandan sayı üretme.
ANALİZ ÜSLUBU: Kurumsal çerçeveler (senaryo analizi, risk-getiri dengesi) kullan.
KİMLİK SINIRI: Belirli bir şirketin çalışanı değilsin.
TAVSİYE SINIRI: Yatırım tavsiyesi vermezsin. Kısa ve net yaz."""

class AskRequest(BaseModel):
    question: str
    system: Optional[str] = None
    context: Optional[Any] = None

class SyncRequest(BaseModel):
    key: str
    data: Any

@app.get("/health")
async def health():
    r = await _get_redis()
    return {"status": "ok", "model": MODEL, "key_configured": bool(ANTHROPIC_API_KEY), "sync": "active", "storage": "redis" if r else "memory"}

@app.post("/agent/ask")
async def ask(req: AskRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY tanımlı değil.")
    system_prompt = req.system or DEFAULT_SYSTEM_PROMPT
    user_content = req.question.strip()
    if req.context:
        user_content = f"Güncel veri:\n{json.dumps(req.context, ensure_ascii=False)}\n\nSoru: {user_content}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": MODEL, "max_tokens": 800, "system": system_prompt, "messages": [{"role": "user", "content": user_content}]},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Anthropic API hatası ({e.response.status_code}).")
    except Exception as e:
        raise HTTPException(500, "Asistana ulaşılamadı.")
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    return {"answer": text or "Yanıt alınamadı."}

@app.put("/sync/push")
async def sync_push(req: SyncRequest):
    if req.key != SYNC_KEY:
        raise HTTPException(403, "Geçersiz anahtar.")
    import datetime
    payload = {"data": req.data, "updated_at": datetime.datetime.utcnow().isoformat()}
    await store_set("sync", payload)
    return {"status": "ok", "updated_at": payload["updated_at"]}

@app.get("/sync/pull")
async def sync_pull(key: str):
    if key != SYNC_KEY:
        raise HTTPException(403, "Geçersiz anahtar.")
    stored = await store_get("sync")
    if not stored:
        return {"data": None, "updated_at": None}
    return {"data": stored.get("data"), "updated_at": stored.get("updated_at")}
Yapıştırıp "Commit changes" tıklayın.







Claude is AI and can make mistakes. Please double-check responses.








