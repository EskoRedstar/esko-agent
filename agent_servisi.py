"""
agent_servisi.py
=================
ESKO Analiz Asistanı için backend. Frontend (esko-pwa) zaten her soruyla
birlikte güncel fiyat/portföy/alarm verisini gönderiyor (bkz. index.html
içindeki contextSnapshot()), bu yüzden bu servisin ayrı bir veritabanına
bağlanmasına gerek yok — sadece Claude API'yi GÜVENLİ şekilde (anahtar
sunucuda kalır, tarayıcıya hiç gitmez) çağırıyor.

Ayrıca /sync/* uç noktaları ile cihazlar arası veri senkronizasyonu da
destekleniyor (vadeli hesaplar, alarmlar, alım kayıtları).

Kurulum (yerel test için):
    pip install -r requirements.txt
    cp .env.example .env   # sonra ANTHROPIC_API_KEY'i doldurun
    uvicorn agent_servisi:app --reload --port 8001

Deploy: README-agent.md içindeki adımları izleyin (fiyat servisiyle aynı yöntem).
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
SYNC_KEY = os.environ.get("ESKO_SYNC_KEY", "esko-default")  # Render'dan değiştirin

app = FastAPI(title="ESKO Analiz Asistanı")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "PUT"],
    allow_headers=["*"],
)

DEFAULT_SYSTEM_PROMPT = """Sen ESKO dashboard'unun finansal analiz asistanısın, Türkçe konuşursun.

VERİ KULLANIMI: Sana verilen güncel veriyi kullan, hafızandan sayı üretme.

ANALİZ ÜSLUBU: Büyük kurumsal varlık yöneticilerinin halka açık raporlarında
kullandığı türden çerçeveleri (senaryo analizi, risk-getiri dengesi,
çeşitlendirme) uygula — sadece "fiyat şu kadar arttı" deme, bağlama otur.

KİMLİK SINIRI: Belirli bir şirketin (BlackRock, Vanguard vb.) çalışanı veya
temsilcisi değilsin, öyleymiş gibi davranmazsın.

TAVSİYE SINIRI: Yatırım tavsiyesi vermezsin, "al/sat" önerisi yapmazsın.
Bilgi ve senaryo sunarsın, kararın kullanıcıya ait olduğunu hatırlatırsın.

Kısa ve net yaz."""

# ============================================================
# Bellek-içi senkronizasyon deposu
# (Render'ın ücretsiz katmanı her restart'ta sıfırlar — yeterli
# sıklıkta kullanılırsa veri korunur. Kalıcı depo için
# Render'a bir Redis eklenebilir ama şimdilik bu yeterli.)
# ============================================================
_sync_store: dict[str, Any] = {}


class AskRequest(BaseModel):
    question: str
    system: Optional[str] = None
    context: Optional[Any] = None


class SyncRequest(BaseModel):
    key: str        # Örn: "esko-default" (Render'da ESKO_SYNC_KEY ile ayarlanır)
    data: Any       # Senkronize edilecek veri (JSON)


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL, "key_configured": bool(ANTHROPIC_API_KEY), "sync": "active"}


@app.post("/agent/ask")
async def ask(req: AskRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "Sunucuda ANTHROPIC_API_KEY tanımlı değil.")
    if not req.question or not req.question.strip():
        raise HTTPException(400, "Soru boş olamaz.")

    system_prompt = req.system or DEFAULT_SYSTEM_PROMPT
    user_content = req.question.strip()
    if req.context:
        user_content = f"Güncel veri (JSON):\n{json.dumps(req.context, ensure_ascii=False)}\n\nSoru: {user_content}"

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 800,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_content}],
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        log.error(f"Anthropic API hatası: {e.response.text}")
        raise HTTPException(502, f"Anthropic API hatası ({e.response.status_code}).")
    except Exception as e:
        log.error(f"Beklenmeyen hata: {e}")
        raise HTTPException(500, "Asistana ulaşılamadı.")

    text = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    )
    return {"answer": text or "Yanıt alınamadı."}


# ============================================================
# Senkronizasyon uç noktaları
# ============================================================

@app.put("/sync/push")
async def sync_push(req: SyncRequest):
    """Cihazdan sunucuya veri yükle (Mac veya iPhone'dan herhangi biri değişince çağrılır)."""
    if req.key != SYNC_KEY:
        raise HTTPException(403, "Geçersiz senkronizasyon anahtarı.")
    _sync_store["data"] = req.data
    _sync_store["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
    log.info(f"Sync push: veri güncellendi")
    return {"status": "ok", "updated_at": _sync_store["updated_at"]}


@app.get("/sync/pull")
async def sync_pull(key: str):
    """Sunucudan cihaza veri çek."""
    if key != SYNC_KEY:
        raise HTTPException(403, "Geçersiz senkronizasyon anahtarı.")
    if "data" not in _sync_store:
        return {"data": None, "updated_at": None}
    return {"data": _sync_store["data"], "updated_at": _sync_store.get("updated_at")}

