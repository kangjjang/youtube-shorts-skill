"""Gemini API 기반 주제 선정"""
import json
import logging
from google import genai
from config import Config

log = logging.getLogger("shorts.topic")


def _load_prompt() -> str:
    return (Config.PROMPTS_DIR / "topic_research.md").read_text(encoding="utf-8")


def select_topics(trends: dict) -> dict:
    """트렌드 데이터 → Gemini → 상위 3개 후보 추출"""
    Config.validate(need_gemini=True)

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    system_prompt = _load_prompt()

    trends_text = json.dumps(trends["top_topics"], ensure_ascii=False, indent=2)

    log.info("Gemini에 주제 분석 요청 중...")
    response = client.models.generate_content(
        model=Config.GEMINI_TEXT_MODEL,
        contents=(
            "아래는 오늘 수집한 트렌드 목록입니다. "
            "숏츠에 적합한 상위 3개 주제를 선정해주세요.\n\n"
            f"```json\n{trends_text}\n```"
        ),
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
        result = json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        log.warning("JSON 파싱 실패, 원본 텍스트 반환")
        result = {"raw_response": response_text}

    log.info("주제 선정 완료")
    return result
