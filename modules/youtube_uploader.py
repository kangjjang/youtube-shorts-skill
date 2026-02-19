"""YouTube Data API v3 — OAuth2 인증 + 재시작 가능한 업로드"""
import json
import time
import random
import logging
import httplib2
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import Config

log = logging.getLogger("shorts.upload")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"

# 재시도 설정
MAX_RETRIES = 5
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


def _get_authenticated_service():
    """OAuth2 인증 → YouTube API 서비스 객체"""
    Config.validate(need_youtube=True)

    creds = None
    token_file = Config.TOKEN_FILE

    # 기존 토큰 로드
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    # 토큰 갱신 또는 새로 인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("토큰 갱신 중...")
            creds.refresh(Request())
        else:
            log.info("브라우저에서 YouTube 인증을 진행하세요...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(Config.CLIENT_SECRET_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # 토큰 저장
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        log.info("인증 토큰 저장: %s", token_file)

    return build(YOUTUBE_API_SERVICE, YOUTUBE_API_VERSION, credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = "28",
    privacy: str = "private",
) -> str | None:
    """YouTube에 영상 업로드 (재시작 가능한 resumable upload)

    Args:
        video_path: 영상 파일 경로
        title: 영상 제목
        description: 영상 설명
        tags: 태그 목록
        category_id: 카테고리 ID (28 = 과학/기술)
        privacy: public / unlisted / private

    Returns:
        업로드된 영상 ID 또는 None
    """
    if not Path(video_path).exists():
        log.error("영상 파일이 없습니다: %s", video_path)
        return None

    youtube = _get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path, chunksize=256 * 1024, resumable=True, mimetype="video/mp4"
    )

    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    log.info("업로드 시작: %s (%s)", title, privacy)
    return _resumable_upload(request)


def _resumable_upload(request) -> str | None:
    """지수 백오프를 사용한 재시작 가능 업로드"""
    response = None
    retry = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                log.info("  업로드 진행: %d%%", int(status.progress() * 100))
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                retry += 1
                if retry > MAX_RETRIES:
                    log.error("최대 재시도 횟수 초과")
                    return None
                wait = 2**retry + random.random()
                log.warning("  HTTP %d, %.1f초 후 재시도 (%d/%d)",
                            e.resp.status, wait, retry, MAX_RETRIES)
                time.sleep(wait)
            else:
                log.error("업로드 실패: %s", e)
                return None
        except Exception as e:
            retry += 1
            if retry > MAX_RETRIES:
                log.error("최대 재시도 횟수 초과")
                return None
            wait = 2**retry + random.random()
            log.warning("  오류 발생, %.1f초 후 재시도: %s", wait, e)
            time.sleep(wait)

    video_id = response.get("id")
    log.info("업로드 완료! https://youtu.be/%s", video_id)
    return video_id


def upload_from_dir(output_dir: str, privacy: str = "private") -> str | None:
    """출력 디렉토리에서 영상 + SEO 메타데이터로 업로드"""
    out = Path(output_dir)
    video_path = out / "final_shorts.mp4"
    seo_path = out / "seo.json"

    if not video_path.exists():
        log.error("영상 파일이 없습니다: %s", video_path)
        return None

    # SEO 메타데이터 로드
    if seo_path.exists():
        with open(seo_path, encoding="utf-8") as f:
            seo = json.load(f)
        title = seo.get("titles", {}).get("A", "Untitled Shorts")
        description = seo.get("description", "")
        tags = seo.get("tags", [])
    else:
        log.warning("SEO 메타데이터 없음, 기본값 사용")
        title = out.name
        description = ""
        tags = []

    return upload_video(
        str(video_path),
        title=title,
        description=description,
        tags=tags,
        privacy=privacy,
    )
