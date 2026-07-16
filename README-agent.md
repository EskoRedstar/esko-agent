# Esko Analiz Asistanı — Backend Kurulumu

Bu servis, sohbet panelindeki "demo mod" yanıtlarının yerine **gerçek Claude
yanıtları** koyar. Fiyat servisini (fiyat_servisi.py) nasıl deploy ettiyseniz
aynı yöntemi izleyeceksiniz — bu sefer daha az adımda, çünkü önceki
denemelerde karşılaştığımız sorunları baştan çözdük.

---

## 1) Anthropic API anahtarı alma

1. https://console.anthropic.com adresinde hesap açın (veya giriş yapın).
2. Sol menüden **"API Keys"** → **"Create Key"**.
3. Oluşan anahtarı kopyalayın (bir daha tam haliyle gösterilmez, kaybederseniz yenisini oluşturmanız gerekir).

⚠️ Bu anahtar kredi kartı bilgisi gibidir — kimseyle paylaşmayın, sadece
Render'ın Environment sekmesine gireceksiniz, başka hiçbir yere yapıştırmayın.

---

## 2) GitHub'a yükleme

Yeni bir GitHub reposu açın (fiyat servisinden ayrı, karışmasın), bu klasördeki
3 dosyayı yükleyin: `agent_servisi.py`, `requirements.txt`, `.env.example`.

`.env.example`'ı sadece referans için yüklüyorsunuz — gerçek anahtarı hiçbir
zaman bir dosyaya yazıp GitHub'a yüklemeyin, sadece Render'ın Environment
sekmesine girin.

---

## 3) Render'da deploy etme

1. **"New +" → "Web Service"**, GitHub reponuzu bağlayın.
2. **Language** alanının **"Python 3"** olduğunu gözle doğrulayın (fiyat
   servisinde yaşadığımız sorunun kaynağı buydu — bu sefer baştan doğru seçin).
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `uvicorn agent_servisi:app --host 0.0.0.0 --port $PORT`
5. **Environment** sekmesinden ekleyin: `ANTHROPIC_API_KEY` = (1. adımda kopyaladığınız anahtar)
6. **"Create Web Service"** — birkaç dakika içinde bir adres verecek, örn:
   `https://esko-agent-xxxx.onrender.com`

---

## 4) Doğrulama

Tarayıcıda `https://esko-agent-xxxx.onrender.com/health` açın. Şunu görmelisiniz:
```json
{"status": "ok", "model": "claude-sonnet-4-6", "key_configured": true}
```
`"key_configured": false` görürseniz, Environment sekmesindeki anahtarı kontrol edin.

---

## 5) Frontend'e bağlama

Bu adımı benimle birlikte yapacağız — Render'ın verdiği adresi bana söyleyin,
`esko-pwa` paketindeki `AGENT_ENDPOINT` değişkenini güncelleyip size yeni
zip'i vereceğim. Hiç kod düzenlemeniz gerekmeyecek.

---

## 6) Maliyet notu

Bu servis her sohbet mesajında Anthropic API'ye bir istek gönderir ve bu
istekler Anthropic hesabınızdaki krediyi kullanır (ücretsiz değildir, ancak
küçük ölçekli kullanım için maliyeti düşüktür). console.anthropic.com'daki
"Usage" sayfasından harcamanızı takip edebilirsiniz.
