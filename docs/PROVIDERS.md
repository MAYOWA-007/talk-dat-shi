# Provider Support

Talk Dat! has a provider registry so users can choose a brand, model, mode/trim, API base, and key from Settings or first-run onboarding.

## Wired Adapters

These providers can currently run inside the app.

| Provider | Mode | Notes |
| --- | --- | --- |
| Deepgram | Streaming | Best default for live push-to-talk. Uses Deepgram WebSocket streaming on `/v1/listen`. Flux models need the `/v2/listen` protocol and are not wired yet. |
| OpenAI | Batch | Records locally, then sends WAV audio after release. Includes GPT-4o Transcribe, GPT-4o Mini Transcribe, GPT-4o Transcribe Diarize (auto chunking is sent for clips over 30s), and Whisper-1. |
| Groq | Batch | Uses an OpenAI-compatible transcription endpoint with Whisper Large v3 and v3 Turbo. |
| Mistral | Batch | Uses an OpenAI-compatible transcription endpoint with Voxtral Mini Transcribe 2 (`voxtral-mini-2602`) choices. |
| Custom OpenAI-Compatible | Batch | Set API base to a server that accepts `POST /v1/audio/transcriptions`. |
| ElevenLabs | Batch | Uses the speech-to-text conversion endpoint. Scribe v2 is the default; ElevenLabs removes Scribe v1 on 2026-07-09. |
| AssemblyAI | Batch | Uploads audio, starts a transcript job, then polls for completion. Universal-3 Pro is the default model. |
| Google Gemini | Batch | Sends WAV audio as inline content to Gemini. Gemini 3.5 Flash is the default; the 2.5 family is deprecated and 2.0 Flash was shut down on 2026-06-01. |

Routing is registry-driven: each provider entry declares an `api_kind`, and the session layer dispatches to the matching adapter. Batch requests retry transient HTTP failures (408/429/5xx and network errors) with short exponential backoff.

Provider-specific advanced options are saved as JSON per provider and passed into wired adapters where supported:

- OpenAI-compatible providers: extra scalar fields are added to the multipart transcription request.
- ElevenLabs: extra scalar fields are added to the speech-to-text request.
- AssemblyAI: extra JSON fields are merged into the transcript job body.
- Gemini: `prompt` can override the default transcription prompt.

## Registered But Adapter-Pending

These providers appear in the model registry so the UI and config are ready, but they still need dedicated authentication/request adapters before they can transcribe in Talk Dat!.

- xAI Grok STT (`POST /v1/stt` is multipart but not OpenAI-compatible)
- Google Cloud Speech
- Microsoft Azure Speech (including the MAI Transcribe preview models)
- Amazon Transcribe
- Speechmatics
- Cohere Transcribe (`POST /v2/audio/transcriptions`)
- Gladia (Solaria 1 and Solaria 3)
- Rev AI
- NVIDIA / Riva / NIM style ASR
- Alibaba / DashScope (Qwen3-ASR Flash, Qwen3-Omni Flash)
- Local open-weights runners

## Model Registry Freshness

Model IDs in `knight_flow/stt_registry.py` were last verified against official provider docs on 2026-06-12. Notable lifecycle dates:

- ElevenLabs `scribe_v1` is removed on 2026-07-09.
- Google `gemini-2.0-flash` was shut down on 2026-06-01; the 2.5 family is deprecated.
- Groq `distil-whisper-large-v3-en` is deprecated in favor of `whisper-large-v3-turbo`.
- AssemblyAI `slam-1` is deprecated; Universal-3 Pro is current.

The model picker accepts free-typed model IDs, so newly released models can be used before the registry is updated.

## API Key Storage

Keys are not stored in the repo. User-entered keys are saved only in:

```text
%APPDATA%\TalkDat\config.json
```

Users may also provide keys through environment variables such as `DEEPGRAM_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `ELEVENLABS_API_KEY`, `ASSEMBLYAI_API_KEY`, and `GEMINI_API_KEY`.

Custom dictionary words, snippets, provider advanced options, transcript history, live drafts, and scratchpad tabs are also user-private local files under `%APPDATA%\TalkDat`. Public GitHub downloads start empty.

## Adding A Provider

1. Add or update the provider entry in `knight_flow/stt_registry.py`.
2. Add a session implementation in `knight_flow/stt_sessions.py`.
3. Map provider-specific request parameters into a small stable config shape.
4. Keep API keys out of logs and UI status snapshots.
5. Add a smoke test or manual checklist item for activation, no-speech timeout, and cancel.
