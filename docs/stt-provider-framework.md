# Talk Dat Shi STT Provider Framework

Talk Dat Shi now separates speech-to-text selection into a provider registry and runtime session adapters.

## Runtime Lanes

- `streaming`: microphone audio is sent while the user is actively holding or using hands-free mode. Deepgram uses this path today.
- `batch`: microphone audio is recorded locally first, then sent after the user releases or stops the session. This keeps hover/idle credit-safe and supports leaderboard models that do not expose a realtime API.
- `external`: the model is visible in Settings for planning and public customization, but needs a dedicated adapter, signed cloud auth flow, SDK, or local runner before it can execute.

## Wired Adapters

- Deepgram live streaming: `deepgram_stream`
- OpenAI-compatible batch transcription: OpenAI, Groq, xAI, Mistral, and custom OpenAI-compatible endpoints
- ElevenLabs batch transcription
- AssemblyAI upload/transcript/poll batch transcription
- Google Gemini audio batch transcription

## Registered Provider Families

- Deepgram: Nova, Enhanced, Base, Whisper
- OpenAI: GPT-4o Transcribe, GPT-4o Mini Transcribe, Whisper-1
- ElevenLabs: Scribe v2, Scribe v1
- xAI: Grok speech-to-text models
- Groq: Whisper Large v3 family
- Mistral: Voxtral Mini and Voxtral Small
- AssemblyAI: Universal family
- Google Gemini and Google Cloud Speech
- Microsoft Azure Speech
- Amazon Transcribe
- Speechmatics
- Cohere
- Gladia
- Rev AI
- NVIDIA open-weight ASR families
- Alibaba Qwen speech models
- Custom OpenAI-compatible and local/open-weight runners

## Source Anchors

- Artificial Analysis STT benchmark: https://artificialanalysis.ai/speech-to-text/non-streaming
- Deepgram live streaming docs: https://developers.deepgram.com/docs/live-streaming-audio
- OpenAI transcription API: https://platform.openai.com/docs/api-reference/audio/createTranscription
- ElevenLabs speech-to-text API: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
- AssemblyAI speech-to-text docs: https://www.assemblyai.com/docs/speech-to-text
- Google Gemini audio docs: https://ai.google.dev/gemini-api/docs/audio
- Groq speech-to-text docs: https://console.groq.com/docs/speech-to-text
- AWS Transcribe docs: https://docs.aws.amazon.com/transcribe/latest/dg/what-is-transcribe.html
- Azure Speech-to-text docs: https://learn.microsoft.com/azure/ai-services/speech-service/speech-to-text

## Public Repo Safety

Provider keys are stored only in user config or environment variables. The registry contains public metadata only: provider names, model IDs, capability flags, and docs URLs.
