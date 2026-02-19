"""Gemini TTS 기반 한국어 나레이션 생성"""
import struct
import wave
import logging
from pathlib import Path
from google import genai
from google.genai import types
from config import Config

log = logging.getLogger("shorts.tts")


def generate_narration(script: dict, output_dir: Path) -> dict | None:
    """스크립트 나레이션 → Gemini TTS → WAV 파일 생성

    Returns:
        {"path": str, "duration": float} 또는 실패 시 None
    """
    Config.validate(need_gemini=True)

    narration = script.get("narration", {})
    parts = [
        narration.get("hook", ""),
        narration.get("main", ""),
        narration.get("cta", ""),
    ]
    text = " ".join(p for p in parts if p)

    if not text:
        log.error("나레이션 텍스트가 비어있습니다")
        return None

    log.info("TTS 생성 중 (%d자)...", len(text))

    client = genai.Client(api_key=Config.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore",
                        )
                    )
                ),
            ),
        )

        audio_data = response.candidates[0].content.parts[0].inline_data.data
        output_path = output_dir / "narration.wav"

        # PCM 데이터를 WAV 파일로 저장 (24kHz, 16-bit, mono)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_data)

        # duration 계산
        num_samples = len(audio_data) // 2  # 16-bit = 2 bytes per sample
        duration = num_samples / 24000.0

        log.info("TTS 저장 완료: %s (%.1f초)", output_path, duration)
        return {"path": str(output_path), "duration": duration}

    except Exception as e:
        log.error("TTS 생성 실패: %s", e)
        return None
