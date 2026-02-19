"""Remotion 기반 영상 합성 — Veo 클립 + 자막 + 나레이션"""
import json
import subprocess
import logging
import math
from pathlib import Path
from config import Config

log = logging.getLogger("shorts.compositor")

FPS = 30
REMOTION_DIR = Path(__file__).parent.parent / "remotion"


def _build_props(
    script: dict,
    clips: list[str],
    narration: dict | None,
    output_dir: Path,
) -> dict:
    """Remotion composition-props.json 생성"""
    scenes_data = []
    scenes = script.get("scenes", [])
    subtitles = script.get("subtitles", [])

    # 나레이션 duration 기반 총 프레임 계산 (없으면 클립 합산)
    if narration:
        total_duration_sec = narration["duration"]
    else:
        total_duration_sec = len(clips) * Config.VEO_CLIP_DURATION

    total_frames = math.ceil(total_duration_sec * FPS)

    # 씬별 프레임 균등 분배
    num_scenes = len(clips)
    if num_scenes == 0:
        log.error("합성할 클립이 없습니다")
        return {}

    base_frames = total_frames // num_scenes
    remainder = total_frames % num_scenes

    for i, clip_path in enumerate(clips):
        scene = scenes[i] if i < len(scenes) else {}
        duration_frames = base_frames + (1 if i < remainder else 0)

        # 클립 경로를 output_dir 기준 상대 경로로 변환
        rel_clip = str(Path(clip_path).relative_to(output_dir))

        scenes_data.append({
            "clipFile": rel_clip,
            "textOverlay": scene.get("text_overlay", ""),
            "durationFrames": duration_frames,
        })

    # 나레이션 경로
    narration_file = ""
    if narration:
        narration_file = str(Path(narration["path"]).relative_to(output_dir))

    props = {
        "scenes": scenes_data,
        "subtitles": subtitles,
        "narrationFile": narration_file,
        "totalDurationFrames": total_frames,
    }
    return props


def render(
    script: dict,
    clips: list[str],
    narration: dict | None,
    output_dir: Path,
) -> str | None:
    """Remotion으로 최종 영상 합성

    Returns:
        최종 영상 경로 또는 실패 시 None
    """
    if not clips:
        log.error("합성할 클립이 없습니다")
        return None

    # 1. Props 생성
    props = _build_props(script, clips, narration, output_dir)
    if not props:
        return None

    props_path = output_dir / "composition-props.json"
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)
    log.info("Remotion props 저장: %s", props_path)

    # 2. Remotion 렌더링
    output_path = output_dir / "final_shorts.mp4"

    cmd = [
        "npx", "remotion", "render",
        "src/Root.tsx",
        "ShortsVideo",
        str(output_path),
        f"--props={props_path}",
        f"--public-dir={output_dir}",
        "--width=1080",
        "--height=1920",
        f"--fps={FPS}",
    ]

    log.info("Remotion 렌더링 시작...")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            check=True,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        log.info("렌더링 완료: %s", output_path)
        return str(output_path)

    except FileNotFoundError:
        log.error(
            "npx를 찾을 수 없습니다. Node.js가 설치되어 있는지 확인하세요.\n"
            "  → brew install node && cd remotion && npm install"
        )
        return None
    except subprocess.CalledProcessError as e:
        log.error("Remotion 렌더링 실패:\n%s", e.stderr)
        return None
    except subprocess.TimeoutExpired:
        log.error("Remotion 렌더링 타임아웃 (20분 초과)")
        return None
