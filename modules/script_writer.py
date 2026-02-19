"""Gemini API 기반 60초 한국어 스크립트 작성"""
import json
import logging
from google import genai
from config import Config

log = logging.getLogger("shorts.script")


def _load_prompt() -> str:
    return (Config.PROMPTS_DIR / "script_writer.md").read_text(encoding="utf-8")


def write_script(topic: str, source_url: str = "", summary: str = "") -> dict:
    """주제 → Gemini → 60초 스크립트 + 장면별 프롬프트 JSON"""
    Config.validate(need_gemini=True)

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    system_prompt = _load_prompt()

    user_content = f"주제: {topic}\n"
    if source_url:
        user_content += f"원문 링크: {source_url}\n"
    if summary:
        user_content += f"요약: {summary}\n"
    user_content += "\n위 주제에 대해 60초 숏츠 스크립트를 작성해주세요."

    log.info("스크립트 작성 중: %s", topic)
    response = client.models.generate_content(
        model=Config.GEMINI_TEXT_MODEL,
        contents=user_content,
        config={"system_instruction": system_prompt},
    )

    response_text = response.text
    try:
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text
        script = json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        log.warning("JSON 파싱 실패, 원본 텍스트 반환")
        script = {"raw_response": response_text}

    log.info("스크립트 작성 완료: %d 장면", len(script.get("scenes", [])))
    return script
