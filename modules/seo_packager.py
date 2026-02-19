"""Gemini API 기반 SEO 메타데이터 생성"""
import json
import logging
from google import genai
from config import Config

log = logging.getLogger("shorts.seo")


def _load_prompt() -> str:
    return (Config.PROMPTS_DIR / "seo_packager.md").read_text(encoding="utf-8")


def generate_seo(script: dict) -> dict:
    """스크립트 → Gemini → SEO 업로드 패키지"""
    Config.validate(need_gemini=True)

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    system_prompt = _load_prompt()

    script_text = json.dumps(script, ensure_ascii=False, indent=2)

    log.info("SEO 패키지 생성 중...")
    response = client.models.generate_content(
        model=Config.GEMINI_TEXT_MODEL,
        contents=(
            "아래 스크립트에 대한 YouTube SEO 업로드 패키지를 만들어주세요.\n\n"
            f"```json\n{script_text}\n```"
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
        seo = json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        log.warning("JSON 파싱 실패, 원본 텍스트 반환")
        seo = {"raw_response": response_text}

    log.info("SEO 패키지 생성 완료")
    return seo
