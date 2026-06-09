# Provider Support

Talk Dat Shi has a provider registry so users can choose a brand, model, mode/trim, API base, and key from Settings or first-run onboarding.

## Wired Adapters

These providers can currently run inside the app.

| Provider | Mode | Notes |
| --- | --- | --- |
| Deepgram | Streaming | Best default for live push-to-talk. Uses Deepgram WebSocket streaming. |
| OpenAI | Batch | Records locally, then sends WAV audio after release. |
| Groq | Batch | Uses an OpenAI-compatible transcription endpoint. |
| xAI | Batch | Uses an OpenAI-compatible transcription endpoint. |
| Mistral | Batch | Uses an OpenAI-compatible transcription endpoint. |
| Custom OpenAI-Compatible | Batch | Set API base to a server that accepts `POST /v1/audio/transcriptions`. |
| ElevenLabs | Batch | Uses the speech-to-text conversion endpoint. |
| AssemblyAI | Batch | Uploads audio, starts a transcript job, then polls for completion. |
| Google Gemini | Batch | Sends WAV audio as inline content to Gemini. |

## Registered But Adapter-Pending

These providers appear in the model registry so the UI and config are ready, but they still need dedicated authentication/request adapters before they can transcribe in Talk Dat Shi.

- Google Cloud Speech
- Microsoft Azure Speech
- Amazon Transcribe
- Speechmatics
- Cohere
- Gladia
- Rev AI
- NVIDIA / Riva / NIM style ASR
- Alibaba / DashScope
- Local open-weights runners

## API Key Storage

Keys are not stored in the repo. User-entered keys are saved only in:

```text
%APPDATA%\TalkDatShi\config.json
```

Users may also provide keys through environment variables such as `DEEPGRAM_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `ELEVENLABS_API_KEY`, `ASSEMBLYAI_API_KEY`, and `GEMINI_API_KEY`.

## Adding A Provider

1. Add or update the provider entry in `knight_flow/stt_registry.py`.
2. Add a session implementation in `knight_flow/stt_sessions.py`.
3. Map provider-specific request parameters into a small stable config shape.
4. Keep API keys out of logs and UI status snapshots.
5. Add a smoke test or manual checklist item for activation, no-speech timeout, and cancel.
