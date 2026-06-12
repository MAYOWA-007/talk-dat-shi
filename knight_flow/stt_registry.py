from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .local_stt import LOCAL_MODELS


@dataclass(frozen=True)
class STTModel:
    id: str
    label: str
    mode: str
    variants: tuple[str, ...] = ("default",)
    notes: str = ""
    open_weights: bool = False


@dataclass(frozen=True)
class STTProvider:
    id: str
    label: str
    api_kind: str
    env_key: str
    docs_url: str
    key_label: str = "API key"
    key_optional: bool = False
    supports_streaming: bool = False
    supports_batch: bool = True
    models: tuple[STTModel, ...] = field(default_factory=tuple)
    api_base: str = ""
    notes: str = ""


PROVIDERS: tuple[STTProvider, ...] = (
    STTProvider(
        id="deepgram",
        label="Deepgram",
        api_kind="deepgram_stream",
        env_key="DEEPGRAM_API_KEY",
        docs_url="https://developers.deepgram.com/docs/live-streaming-audio",
        supports_streaming=True,
        supports_batch=True,
        api_base="https://api.deepgram.com",
        models=(
            STTModel("nova-3", "Nova-3", "streaming", ("streaming",)),
            STTModel("nova-3-general", "Nova-3 General", "streaming", ("streaming",)),
            STTModel("nova-3-medical", "Nova-3 Medical", "streaming", ("streaming",)),
            STTModel("nova-2", "Nova-2", "streaming", ("streaming",)),
            STTModel("nova-2-general", "Nova-2 General", "streaming", ("streaming",)),
            STTModel("nova-2-meeting", "Nova-2 Meeting", "streaming", ("streaming",)),
            STTModel("nova-2-phonecall", "Nova-2 Phone Call", "streaming", ("streaming",)),
            STTModel("nova-2-finance", "Nova-2 Finance", "streaming", ("streaming",)),
            STTModel("nova-2-conversationalai", "Nova-2 Conversational AI", "streaming", ("streaming",)),
            STTModel("nova-2-voicemail", "Nova-2 Voicemail", "streaming", ("streaming",)),
            STTModel("nova-2-video", "Nova-2 Video", "streaming", ("streaming",)),
            STTModel("enhanced", "Enhanced", "streaming", ("streaming",)),
            STTModel("base", "Base", "streaming", ("streaming",)),
            STTModel("whisper", "Whisper", "batch"),
        ),
        notes="Flux (flux-general-en) needs the /v2/listen protocol and is not wired yet.",
    ),
    STTProvider(
        id="openai",
        label="OpenAI",
        api_kind="openai_batch",
        env_key="OPENAI_API_KEY",
        docs_url="https://platform.openai.com/docs/api-reference/audio/createTranscription",
        api_base="https://api.openai.com",
        models=(
            STTModel("gpt-4o-transcribe", "GPT-4o Transcribe", "batch", ("json", "text")),
            STTModel("gpt-4o-mini-transcribe", "GPT-4o Mini Transcribe", "batch", ("json", "text")),
            STTModel("gpt-4o-transcribe-diarize", "GPT-4o Transcribe Diarize", "batch", ("diarized_json", "json")),
            STTModel("whisper-1", "Whisper-1", "batch", ("json", "text")),
        ),
    ),
    STTProvider(
        id="elevenlabs",
        label="ElevenLabs",
        api_kind="elevenlabs_batch",
        env_key="ELEVENLABS_API_KEY",
        docs_url="https://elevenlabs.io/docs/api-reference/speech-to-text/convert",
        key_label="ElevenLabs API key",
        api_base="https://api.elevenlabs.io",
        models=(
            STTModel("scribe_v2", "Scribe v2", "batch", ("default", "diarize", "tag-audio-events")),
            STTModel(
                "scribe_v1",
                "Scribe v1 (deprecated)",
                "batch",
                ("default", "diarize", "tag-audio-events"),
                notes="ElevenLabs removes scribe_v1 on 2026-07-09. Use Scribe v2.",
            ),
        ),
    ),
    STTProvider(
        id="xai",
        label="xAI",
        api_kind="external",
        env_key="XAI_API_KEY",
        docs_url="https://docs.x.ai/developers/model-capabilities/audio/speech-to-text",
        api_base="https://api.x.ai",
        models=(
            STTModel("grok-transcribe", "Grok STT", "batch", ("default", "diarize")),
        ),
        notes="xAI STT uses POST /v1/stt (multipart), not the OpenAI-compatible audio endpoint. Adapter pending.",
    ),
    STTProvider(
        id="groq",
        label="Groq",
        api_kind="openai_batch",
        env_key="GROQ_API_KEY",
        docs_url="https://console.groq.com/docs/speech-to-text",
        api_base="https://api.groq.com/openai",
        models=(
            STTModel("whisper-large-v3", "Whisper Large v3", "batch", ("json", "verbose_json")),
            STTModel("whisper-large-v3-turbo", "Whisper Large v3 Turbo", "batch", ("json", "verbose_json")),
        ),
    ),
    STTProvider(
        id="mistral",
        label="Mistral",
        api_kind="openai_batch",
        env_key="MISTRAL_API_KEY",
        docs_url="https://docs.mistral.ai/capabilities/audio/",
        api_base="https://api.mistral.ai",
        models=(
            STTModel("voxtral-mini-2602", "Voxtral Mini Transcribe 2", "batch", ("json", "text")),
            STTModel("voxtral-mini-latest", "Voxtral Mini (latest)", "batch", ("json", "text")),
            STTModel(
                "voxtral-small-latest",
                "Voxtral Small",
                "batch",
                ("json", "text"),
                notes="Audio-understanding model; transcription capped around 15 minutes.",
            ),
        ),
    ),
    STTProvider(
        id="assemblyai",
        label="AssemblyAI",
        api_kind="assemblyai_batch",
        env_key="ASSEMBLYAI_API_KEY",
        docs_url="https://www.assemblyai.com/docs/speech-to-text",
        supports_streaming=True,
        supports_batch=True,
        api_base="https://api.assemblyai.com",
        models=(
            STTModel("universal-3-pro", "Universal-3 Pro", "batch", ("default", "speaker-labels")),
            STTModel("universal-2", "Universal-2", "batch", ("default", "speaker-labels")),
            STTModel("universal", "Universal", "batch", ("default", "speaker-labels")),
        ),
    ),
    STTProvider(
        id="google_gemini",
        label="Google Gemini",
        api_kind="gemini_batch",
        env_key="GEMINI_API_KEY",
        docs_url="https://ai.google.dev/gemini-api/docs/audio",
        api_base="https://generativelanguage.googleapis.com",
        models=(
            STTModel("gemini-3.5-flash", "Gemini 3.5 Flash", "batch", ("default", "low-latency")),
            STTModel("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite", "batch", ("default", "low-latency")),
            STTModel(
                "gemini-2.5-pro",
                "Gemini 2.5 Pro (deprecated)",
                "batch",
                ("default", "high-accuracy"),
                notes="Gemini 2.5 family is deprecated; migrate to 3.x.",
            ),
            STTModel(
                "gemini-2.5-flash",
                "Gemini 2.5 Flash (deprecated)",
                "batch",
                ("default", "low-latency"),
                notes="Gemini 2.5 family is deprecated; migrate to 3.x.",
            ),
        ),
        notes="Gemini 2.0 Flash was shut down on 2026-06-01 and no longer transcribes.",
    ),
    STTProvider(
        id="google_cloud",
        label="Google Cloud Speech",
        api_kind="external",
        env_key="GOOGLE_APPLICATION_CREDENTIALS",
        docs_url="https://cloud.google.com/speech-to-text/docs",
        key_label="Service account path",
        supports_streaming=True,
        supports_batch=True,
        models=(
            STTModel("chirp_3", "Chirp 3", "streaming", ("default", "enhanced")),
            STTModel("chirp", "Chirp", "streaming", ("default",)),
            STTModel("latest_long", "Latest Long", "batch", ("default",)),
            STTModel("latest_short", "Latest Short", "streaming", ("default",)),
        ),
        notes="Needs Google service-account auth, not a simple bearer key.",
    ),
    STTProvider(
        id="azure",
        label="Microsoft Azure Speech",
        api_kind="external",
        env_key="AZURE_SPEECH_KEY",
        docs_url="https://learn.microsoft.com/azure/ai-services/speech-service/speech-to-text",
        key_label="Azure Speech key",
        supports_streaming=True,
        supports_batch=True,
        models=(
            STTModel("latest", "Speech to Text", "streaming", ("region-required", "custom-endpoint")),
            STTModel("mai-transcribe-1.5", "MAI Transcribe 1.5", "batch", ("preview",)),
            STTModel("mai-transcribe-1", "MAI Transcribe 1", "batch", ("preview",)),
        ),
        notes="Requires Azure region and usually SDK/service setup. MAI Transcribe runs via the LLM Speech API preview.",
    ),
    STTProvider(
        id="aws",
        label="Amazon Transcribe",
        api_kind="external",
        env_key="AWS_ACCESS_KEY_ID",
        docs_url="https://docs.aws.amazon.com/transcribe/latest/dg/what-is-transcribe.html",
        key_label="AWS access key",
        supports_streaming=True,
        supports_batch=True,
        models=(
            STTModel("transcribe", "Amazon Transcribe", "streaming", ("standard", "medical", "call-analytics")),
        ),
        notes="Job-based service without public model IDs. Requires AWS signed requests and region/secret configuration.",
    ),
    STTProvider(
        id="speechmatics",
        label="Speechmatics",
        api_kind="external",
        env_key="SPEECHMATICS_API_KEY",
        docs_url="https://docs.speechmatics.com/",
        supports_streaming=True,
        supports_batch=True,
        models=(
            STTModel("enhanced", "Enhanced", "batch", ("default", "diarization")),
            STTModel("standard", "Standard", "streaming", ("default",)),
        ),
    ),
    STTProvider(
        id="cohere",
        label="Cohere",
        api_kind="external",
        env_key="COHERE_API_KEY",
        docs_url="https://docs.cohere.com/v2/docs/transcribe",
        api_base="https://api.cohere.com",
        models=(
            STTModel(
                "cohere-transcribe-03-2026",
                "Cohere Transcribe",
                "batch",
                ("default",),
                open_weights=True,
            ),
        ),
        notes="Uses POST /v2/audio/transcriptions (not OpenAI-compatible). Adapter pending.",
    ),
    STTProvider(
        id="gladia",
        label="Gladia",
        api_kind="external",
        env_key="GLADIA_API_KEY",
        docs_url="https://docs.gladia.io/",
        supports_streaming=True,
        supports_batch=True,
        models=(
            STTModel("solaria-1", "Solaria 1", "batch", ("default",)),
            STTModel("solaria-3", "Solaria 3", "batch", ("default",), notes="Async only. EN/FR/DE/ES/IT."),
        ),
    ),
    STTProvider(
        id="rev_ai",
        label="Rev AI",
        api_kind="external",
        env_key="REVAI_API_KEY",
        docs_url="https://docs.rev.ai/",
        supports_streaming=True,
        supports_batch=True,
        models=(STTModel("rev-ai", "Rev AI", "batch", ("default",)),),
    ),
    STTProvider(
        id="nvidia",
        label="NVIDIA",
        api_kind="external",
        env_key="NVIDIA_API_KEY",
        docs_url="https://docs.nvidia.com/deeplearning/riva/user-guide/docs/asr/asr-overview.html",
        supports_streaming=True,
        supports_batch=True,
        models=(
            STTModel("parakeet-tdt-0.6b-v3", "Parakeet TDT 0.6B v3", "batch", ("default",), open_weights=True),
            STTModel("canary-1b-v2", "Canary 1B v2", "batch", ("default",), open_weights=True),
            STTModel("canary-qwen-2.5b", "Canary Qwen 2.5B", "batch", ("default",), open_weights=True),
        ),
        notes="Usually runs via Riva/NIM or another NVIDIA-hosted endpoint.",
    ),
    STTProvider(
        id="alibaba",
        label="Alibaba",
        api_kind="external",
        env_key="DASHSCOPE_API_KEY",
        docs_url="https://www.alibabacloud.com/help/en/model-studio/qwen-asr-api-reference",
        models=(
            STTModel("qwen3-asr-flash", "Qwen3-ASR Flash", "batch", ("default",)),
            STTModel("qwen3-omni-flash", "Qwen3-Omni Flash", "batch", ("default",)),
        ),
    ),
    STTProvider(
        id="custom_openai",
        label="Custom OpenAI-Compatible",
        api_kind="openai_batch",
        env_key="CUSTOM_STT_API_KEY",
        docs_url="",
        key_label="Custom API key",
        key_optional=True,
        api_base="",
        supports_batch=True,
        models=(STTModel("custom-model", "custom-model", "batch", ("json", "text")),),
        notes="Set API base to a server that accepts POST /v1/audio/transcriptions.",
    ),
    STTProvider(
        id="local",
        label="Local / On-Device",
        api_kind="local_batch",
        env_key="",
        docs_url="https://github.com/istupakov/onnx-asr",
        key_label="No key needed",
        key_optional=True,
        supports_streaming=False,
        supports_batch=True,
        models=tuple(
            STTModel(
                local_model.id,
                local_model.label,
                "batch",
                ("auto",),
                notes=f"{local_model.languages}. ~{local_model.size_mb} MB download. {local_model.notes}".strip(),
                open_weights=True,
            )
            for local_model in LOCAL_MODELS
        ),
        notes="Runs fully on this PC. Models download once into the TalkDat models folder; audio never leaves the machine.",
    ),
)


PROVIDER_BY_ID = {provider.id: provider for provider in PROVIDERS}


def provider_labels() -> list[str]:
    return [provider.label for provider in PROVIDERS]


def provider_id_for_label(label: str) -> str:
    for provider in PROVIDERS:
        if provider.label == label or provider.id == label:
            return provider.id
    return "deepgram"


def provider_label(provider_id: str) -> str:
    return PROVIDER_BY_ID.get(provider_id, PROVIDER_BY_ID["deepgram"]).label


def models_for_provider(provider_id: str) -> tuple[STTModel, ...]:
    return PROVIDER_BY_ID.get(provider_id, PROVIDER_BY_ID["deepgram"]).models


def model_labels(provider_id: str) -> list[str]:
    return [model.label for model in models_for_provider(provider_id)]


def model_for_id(provider_id: str, model_id: str | None) -> STTModel:
    models = models_for_provider(provider_id)
    for model in models:
        if model.id == model_id or model.label == model_id:
            return model
    if model_id and str(model_id).strip():
        return STTModel(str(model_id).strip(), str(model_id).strip(), models[0].mode, models[0].variants)
    return models[0]


def model_id_for_label(provider_id: str, label: str) -> str:
    for model in models_for_provider(provider_id):
        if model.label == label or model.id == label:
            return model.id
    clean = str(label).strip()
    return clean or models_for_provider(provider_id)[0].id


def model_label(provider_id: str, model_id: str | None) -> str:
    return model_for_id(provider_id, model_id).label


def selected_provider_id(config: dict[str, Any]) -> str:
    stt = config.get("stt", {})
    provider_id = str(stt.get("provider", "deepgram")).strip() or "deepgram"
    if provider_id not in PROVIDER_BY_ID:
        return "deepgram"
    return provider_id


def provider_settings(config: dict[str, Any], provider_id: str | None = None) -> dict[str, Any]:
    provider_id = provider_id or selected_provider_id(config)
    stt = config.setdefault("stt", {})
    providers = stt.setdefault("providers", {})
    settings = providers.setdefault(provider_id, {})
    if provider_id == "deepgram":
        deepgram = config.setdefault("deepgram", {})
        settings.setdefault("api_key", deepgram.get("api_key", ""))
        settings.setdefault("model", deepgram.get("model", "nova-3"))
        settings.setdefault("variant", "streaming")
    provider = PROVIDER_BY_ID.get(provider_id)
    if provider:
        settings.setdefault("model", provider.models[0].id)
        settings.setdefault("variant", provider.models[0].variants[0])
        settings.setdefault("api_base", provider.api_base)
        settings.setdefault("extra", {})
    return settings


def selected_model_id(config: dict[str, Any], provider_id: str | None = None) -> str:
    provider_id = provider_id or selected_provider_id(config)
    settings = provider_settings(config, provider_id)
    if provider_id == "deepgram":
        return str(settings.get("model") or config.get("deepgram", {}).get("model", "nova-3"))
    return str(settings.get("model") or models_for_provider(provider_id)[0].id)


def selected_variant(config: dict[str, Any], provider_id: str | None = None) -> str:
    provider_id = provider_id or selected_provider_id(config)
    model = model_for_id(provider_id, selected_model_id(config, provider_id))
    settings = provider_settings(config, provider_id)
    value = str(settings.get("variant") or model.variants[0])
    return value if value in model.variants else model.variants[0]


def provider_capability_summary(provider_id: str, model_id: str | None = None) -> str:
    provider = PROVIDER_BY_ID.get(provider_id, PROVIDER_BY_ID["deepgram"])
    model = model_for_id(provider.id, model_id)
    caps = []
    if provider.supports_streaming or model.mode == "streaming":
        caps.append("streaming")
    if provider.supports_batch or model.mode == "batch":
        caps.append("batch")
    if model.open_weights:
        caps.append("open weights")
    if provider.api_kind == "external":
        caps.append("adapter pending")
    return " / ".join(caps) or model.mode


def sync_legacy_deepgram(config: dict[str, Any]) -> None:
    settings = provider_settings(config, "deepgram")
    deepgram = config.setdefault("deepgram", {})
    if str(settings.get("api_key", "")).strip():
        deepgram["api_key"] = settings.get("api_key", "")
    if str(settings.get("model", "")).strip():
        deepgram["model"] = settings.get("model", "nova-3")
