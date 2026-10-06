# turkce-tts-api

Kullanıma hazır Türkçe metin-konuşma (TTS) API’si. Docker ile ayağa kalkar; `POST /v1/speak` ile WAV üretir. İsteğe bağlı OpenAI sohbetiyle demo UI üzerinden konuşmalı asistan da denenebilir.

Varsayılan motor: [EMA Lightning](https://pypi.org/project/ema-lightning/). Ağırlıklar ve model kartı: [canberkkkkkk/ema-lightning](https://huggingface.co/canberkkkkkk/ema-lightning) (Apache 2.0). HTTP API motor adını dışarı vermez.

Örnek çıktı (`POST /v1/speak`, “Merhaba, size nasıl yardımcı olabilirim?”):

![Örnek çıktı](samples/demo.mp4)

| Servis | Adres | Açıklama |
|--------|--------|----------|
| **UI** | http://127.0.0.1:3000 | Nginx + `ui/` test arayüzü |
| **TTS API** | http://127.0.0.1:8000 | FastAPI (`POST /v1/speak`) |

UI, API’ye nginx üzerinden proxy eder (`/v1/*`, `/health`). `ui/` host’tan mount edilir; arayüz değişince image rebuild gerekmez.

## Hızlı başlangıç

```bash
docker compose up --build -d
```

- Arayüz: http://127.0.0.1:3000  
- API health: http://127.0.0.1:8000/health  

İlk açılışta model indirilir; healthcheck `start_period` ~3 dk. Model önbelleği `turkce-tts-api-model-cache` volume’unda kalır.

Durdurmak için:

```bash
docker compose down
```

Portlar: `PORT=8000 UI_PORT=3000 docker compose up -d`

TTS kodu değişince: `docker compose up -d --build tts`  
UI düzenleyince: tarayıcıyı yenile.

## Ne yapar?

- **TTS API** — Metni sese çevirir, `audio/wav` döner (`speed`, `seed`, `sample_rate` opsiyonel).
- **Sohbet (opsiyonel)** — `OPENAI_API_KEY` varsa `POST /v1/chat` SSE ile kısa Türkçe yanıt üretir; UI yanıtı cümle cümle seslendirir. Anahtar yoksa yalnızca TTS çalışır.

## API

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/speak \
  -H 'content-type: application/json' \
  -d '{"text":"Merhaba, size nasıl yardımcı olabilirim?"}' \
  --output out.wav
```

| Endpoint | Açıklama |
|----------|----------|
| `GET /health` | Model yüklü mü, chat açık mı |
| `POST /v1/speak` | `{ "text": "..." }` → WAV |
| `POST /v1/chat` | Mesaj geçmişi → SSE token akışı (API key gerekir) |

## Ortam değişkenleri

`.env.example` dosyasını kopyalayın:

```bash
cp .env.example .env
```

| Değişken | Açıklama |
|----------|----------|
| `OPENAI_API_KEY` | Sohbet için (yoksa LLM kapalı) |
| `OPENAI_MODEL` | Varsayılan `gpt-4o-mini` |
| `OPENAI_MAX_TOKENS` | Varsayılan `160` |

`.env` git’e eklenmez.

## Yapı

```
app/           # FastAPI (TTS adapter + chat)
ui/            # Statik arayüz + nginx.conf
samples/       # Örnek ses (demo.mp4, demo.wav)
Dockerfile     # API imajı (CPU torch)
docker-compose.yml
```

## Docker’sız API

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

UI için `docker compose up ui` (API’nin ayakta olması gerekir) veya herhangi bir static dosya sunucusu.
