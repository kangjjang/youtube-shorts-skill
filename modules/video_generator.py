"""Veo 3.1 기반 영상 클립 생성 + FFmpeg 결합"""
import json
import time
import subprocess
import logging
from pathlib import Path
from google import genai
from google.genai import types
from config import Config

log = logging.getLogger("shorts.video")


def estimate_cost(num_clips: int, quality: str = "fast") -> float:
    """예상 비용 계산"""
    cost_per_sec = Config.VEO_COST_FAST if quality == "fast" else Config.VEO_COST_FULL
    return cost_per_sec * Config.VEO_CLIP_DURATION * num_clips


def _generate_clip(
    client, image_path: str, prompt: str, output_path: str, use_fast: bool = True
) -> bool:
    """이미지를 첫 프레임으로 Veo 3.1 영상 클립 생성"""
    model = "veo-3.1-fast-generate-preview" if use_fast else "veo-3.1-generate-preview"
    cost_per_sec = Config.VEO_COST_FAST if use_fast else Config.VEO_COST_FULL

    log.info(
        "클립 생성: %s (%s, 예상비용: $%.2f)",
        Path(image_path).name,
        model,
        cost_per_sec * Config.VEO_CLIP_DURATION,
    )

    try:
        image = types.Image.from_file(location=image_path)

        operation = client.models.generate_videos(
            model=model,
            prompt=(
                f"9:16 vertical portrait video for YouTube Shorts. {prompt}. "
                "Smooth motion, tech aesthetic, dark background."
            ),
            image=image,
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=Config.VEO_CLIP_DURATION,
            ),
        )

        log.info("  생성 대기 중...")
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        video = operation.result.generated_videos[0]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        client.files.download(file=video.video)
        video.video.save(output_path)
        log.info("  저장 완료: %s", output_path)
        return True

    except Exception as e:
        log.warning("  클립 생성 실패: %s", e)
        return False


def generate_clips(
    frames: list[dict], script: dict, output_dir: Path, quality: str = "fast"
) -> list[str]:
    """프레임 이미지 → Veo 클립 생성"""
    Config.validate(need_gemini=True)

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    use_fast = quality == "fast"
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    scenes = script.get("scenes", [])
    log.info(
        "%d개 클립 생성 시작 (Veo 3.1 %s)", len(frames), "Fast" if use_fast else "Full"
    )
    log.info("예상 총 비용: $%.2f", estimate_cost(len(frames), quality))

    clips = []
    for frame_info in frames:
        scene_idx = frame_info["scene"] - 1
        scene = scenes[scene_idx] if scene_idx < len(scenes) else {}
        video_prompt = scene.get("veo_prompt", frame_info.get("prompt", ""))
        output_path = str(clips_dir / f"clip_{frame_info['scene']:02d}.mp4")

        success = _generate_clip(
            client, frame_info["path"], video_prompt, output_path, use_fast=use_fast
        )
        if success:
            clips.append(output_path)
        else:
            log.warning("클립 %d 건너뜀", frame_info["scene"])

    log.info("%d/%d개 클립 생성 완료", len(clips), len(frames))
    return clips


def concat_clips(clips: list[str], output_dir: Path) -> str | None:
    """FFmpeg로 클립 결합 → final_shorts.mp4"""
    if not clips:
        log.error("결합할 클립이 없습니다")
        return None

    concat_list = output_dir / "clips" / "concat_list.txt"
    with open(concat_list, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    output_path = str(output_dir / "final_shorts.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        log.info("최종 영상 생성: %s", output_path)
        return output_path
    except FileNotFoundError:
        log.error("ffmpeg가 설치되어 있지 않습니다. brew install ffmpeg")
        return None
    except subprocess.CalledProcessError as e:
        log.error("ffmpeg 실패: %s", e.stderr)
        return None
