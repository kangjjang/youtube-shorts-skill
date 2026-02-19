"""Gemini 2.5 Flash 기반 키프레임 이미지 생성"""
import json
import logging
from pathlib import Path
from google import genai
from config import Config

log = logging.getLogger("shorts.image")


def _generate_frame(client, prompt: str, output_path: str) -> bool:
    """Gemini 2.5 Flash Image로 이미지 1장 생성"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=(
                "Create a tech-focused YouTube Shorts thumbnail image "
                "for a Korean developer audience.\n"
                "9:16 portrait format, 1080x1920px equivalent.\n"
                "Style: dark background, modern tech aesthetic, neon accents.\n"
                f"Content: {prompt}\n"
                "No text overlays — clean visual only."
            ),
            config={"response_modalities": ["IMAGE"]},
        )
        for part in response.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                with open(output_path, "wb") as f:
                    f.write(part.inline_data.data)
                log.info("이미지 저장: %s", output_path)
                return True
        return False
    except Exception as e:
        log.warning("이미지 생성 실패: %s", e)
        return False


def generate_frames(script: dict, output_dir: Path) -> list[dict]:
    """스크립트의 장면별 키프레임 이미지 생성"""
    Config.validate(need_gemini=True)

    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    scenes = script.get("scenes", [])
    log.info("%d개 장면 이미지 생성 시작 (Gemini 2.5 Flash Image)", len(scenes))

    generated = []
    for i, scene in enumerate(scenes):
        output_path = frames_dir / f"frame_{i + 1:02d}.png"
        success = _generate_frame(client, scene["visual_prompt"], str(output_path))
        if success:
            generated.append({
                "scene": i + 1,
                "path": str(output_path),
                "prompt": scene["visual_prompt"],
            })
        else:
            log.warning("장면 %d 건너뜀", i + 1)

    # 매니페스트 저장
    manifest_path = frames_dir / "frames_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(generated, f, ensure_ascii=False, indent=2)

    log.info("%d/%d개 이미지 생성 완료", len(generated), len(scenes))
    return generated
