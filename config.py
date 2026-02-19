"""설정 관리 — .env 로딩 및 검증"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("shorts")


class Config:
    """환경변수 기반 설정"""

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    GEMINI_TEXT_MODEL: str = "gemini-2.5-flash"

    # 경로
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    CREDENTIALS_DIR: Path = BASE_DIR / "credentials"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"

    # YouTube OAuth2
    CLIENT_SECRET_FILE: Path = CREDENTIALS_DIR / "client_secret.json"
    TOKEN_FILE: Path = CREDENTIALS_DIR / "token.json"

    # Veo 비용 (달러/초)
    VEO_COST_FAST: float = 0.10
    VEO_COST_FULL: float = 0.30
    VEO_CLIP_DURATION: int = 8

    @classmethod
    def validate(cls, need_gemini=False, need_youtube=False):
        """필수 설정 검증"""
        errors = []
        if need_gemini and not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        if need_youtube and not cls.CLIENT_SECRET_FILE.exists():
            errors.append(
                f"YouTube OAuth2 파일이 없습니다: {cls.CLIENT_SECRET_FILE}\n"
                "  → Google Cloud Console에서 다운로드하세요."
            )
        if errors:
            for e in errors:
                log.error(e)
            sys.exit(1)

    @classmethod
    def make_output_dir(cls, slug: str) -> Path:
        """날짜-슬러그 기반 출력 디렉토리 생성"""
        from datetime import date
        dirname = f"{date.today().isoformat()}-{slug}"
        out = cls.OUTPUTS_DIR / dirname
        out.mkdir(parents=True, exist_ok=True)
        (out / "frames").mkdir(exist_ok=True)
        (out / "clips").mkdir(exist_ok=True)
        return out
