#!/usr/bin/env python3
"""YouTube Shorts 자동화 파이프라인 — CLI 진입점"""
import sys
import json
import argparse
import logging
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, log
from modules.trends import collect_trends
from modules.topic_selector import select_topics
from modules.script_writer import write_script
from modules.image_generator import generate_frames
from modules.video_generator import generate_clips, concat_clips, estimate_cost
from modules.tts_generator import generate_narration
from modules.compositor import render as remotion_render
from modules.seo_packager import generate_seo
from modules.youtube_uploader import upload_from_dir


def cmd_trends(args):
    """트렌드 수집만 실행"""
    trends = collect_trends(top_n=args.top)

    output = Path(args.output)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(trends, f, ensure_ascii=False, indent=2)

    print(f"\n상위 {args.top}개 주제 → {output}")
    for i, item in enumerate(trends["top_topics"], 1):
        print(f"  {i}. [{item['source']}] {item['title']}")


def cmd_generate(args):
    """특정 주제로 콘텐츠 생성"""
    topic = args.topic

    # 슬러그 생성
    slug = topic.lower().replace(" ", "-")[:30]
    output_dir = Config.make_output_dir(slug)
    print(f"\n출력 디렉토리: {output_dir}")

    # 스크립트 작성
    print("\n--- 스크립트 작성 ---")
    script = write_script(topic)
    script_path = output_dir / "script.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"스크립트 저장: {script_path}")

    if "raw_response" in script:
        print("스크립트 JSON 파싱 실패. script.json을 확인하세요.")
        return

    # 이미지 생성
    print("\n--- 키프레임 이미지 생성 ---")
    frames = generate_frames(script, output_dir)
    if not frames:
        print("이미지 생성 실패. 파이프라인 중단.")
        return

    # 비용 체크포인트
    quality = args.quality
    num_clips = len(frames)
    cost = estimate_cost(num_clips, quality)
    print(f"\n--- 비용 체크포인트 ---")
    print(f"  클립 수: {num_clips}")
    print(f"  품질: {quality}")
    print(f"  예상 비용: ${cost:.2f}")

    if not args.auto:
        confirm = input("  영상 생성을 진행하시겠습니까? (y/N): ").strip().lower()
        if confirm != "y":
            print("영상 생성 건너뜀.")
            _generate_seo_and_save(script, output_dir)
            return

    # 영상 클립 생성
    print("\n--- 영상 클립 생성 ---")
    clips = generate_clips(frames, script, output_dir, quality=quality)

    # TTS 나레이션 생성
    print("\n--- TTS 나레이션 생성 ---")
    narration = generate_narration(script, output_dir)
    if narration:
        print(f"나레이션: {narration['path']} ({narration['duration']:.1f}초)")
    else:
        print("나레이션 생성 실패. 나레이션 없이 계속 진행.")

    # Remotion 합성 (Veo 클립 + 자막 + 나레이션)
    if clips:
        print("\n--- Remotion 영상 합성 ---")
        final = remotion_render(script, clips, narration, output_dir)
        if final:
            print(f"최종 영상: {final}")
        else:
            # Remotion 실패 시 FFmpeg 폴백
            print("Remotion 실패. FFmpeg 폴백으로 클립 결합...")
            final = concat_clips(clips, output_dir)
            if final:
                print(f"최종 영상 (폴백): {final}")

    # SEO 패키지
    _generate_seo_and_save(script, output_dir)

    print(f"\n완료! 출력 디렉토리: {output_dir}")

    # 업로드
    if args.upload:
        privacy = "public" if args.public else "private"
        cmd_upload_dir(str(output_dir), privacy)


def _generate_seo_and_save(script: dict, output_dir: Path):
    """SEO 메타데이터 생성 및 저장"""
    print("\n--- SEO 패키지 생성 ---")
    seo = generate_seo(script)
    seo_path = output_dir / "seo.json"
    with open(seo_path, "w", encoding="utf-8") as f:
        json.dump(seo, f, ensure_ascii=False, indent=2)
    print(f"SEO 저장: {seo_path}")


def cmd_upload(args):
    """기존 영상 업로드"""
    privacy = "public" if args.public else "private"
    cmd_upload_dir(args.dir, privacy)


def cmd_upload_dir(output_dir: str, privacy: str = "private"):
    """디렉토리에서 업로드 실행"""
    print(f"\n--- YouTube 업로드 ({privacy}) ---")
    video_id = upload_from_dir(output_dir, privacy=privacy)
    if video_id:
        print(f"업로드 성공: https://youtu.be/{video_id}")
    else:
        print("업로드 실패.")


def cmd_full_pipeline(args):
    """전체 파이프라인 실행"""
    # 1. 트렌드 수집
    print("=== 1/9 트렌드 수집 ===")
    trends = collect_trends()

    # 2. 주제 선정
    print("\n=== 2/9 주제 선정 ===")
    candidates = select_topics(trends)

    # 3. 주제 선택
    topic_list = candidates.get("candidates", [])
    if not topic_list:
        print("주제 후보가 없습니다. 트렌드를 확인하세요.")
        return

    if args.auto:
        selected = topic_list[0]
        print(f"자동 선택: {selected['topic']}")
    else:
        print("\n주제 후보:")
        for i, c in enumerate(topic_list, 1):
            print(f"  {i}. {c['topic']}")
            print(f"     {c.get('summary', '')}")
            print(f"     훅: {c.get('hook', '')}")
        choice = input("\n번호를 선택하세요 (1-3): ").strip()
        try:
            idx = int(choice) - 1
            selected = topic_list[idx]
        except (ValueError, IndexError):
            print("잘못된 선택입니다.")
            return

    topic = selected["topic"]
    slug = selected.get("slug", topic.lower().replace(" ", "-")[:30])
    output_dir = Config.make_output_dir(slug)
    print(f"\n출력 디렉토리: {output_dir}")

    # 트렌드 저장
    trends_path = output_dir / "trends.json"
    with open(trends_path, "w", encoding="utf-8") as f:
        json.dump(trends, f, ensure_ascii=False, indent=2)

    # 4. 스크립트 작성
    print("\n=== 3/9 스크립트 작성 ===")
    script = write_script(
        topic,
        source_url=selected.get("source_url", ""),
        summary=selected.get("summary", ""),
    )
    script_path = output_dir / "script.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    if "raw_response" in script:
        print("스크립트 JSON 파싱 실패. script.json을 확인하세요.")
        return

    # 5. 이미지 생성
    print("\n=== 4/9 이미지 생성 ===")
    frames = generate_frames(script, output_dir)
    if not frames:
        print("이미지 생성 실패.")
        return

    # 비용 체크포인트
    quality = args.quality
    cost = estimate_cost(len(frames), quality)
    print(f"\n--- 비용 체크포인트 ---")
    print(f"  클립 수: {len(frames)}, 품질: {quality}, 예상 비용: ${cost:.2f}")

    if not args.auto:
        confirm = input("  영상 생성 진행? (y/N): ").strip().lower()
        if confirm != "y":
            _generate_seo_and_save(script, output_dir)
            print(f"\n영상 생성 건너뜀. 출력: {output_dir}")
            return

    # 6. 영상 생성
    print("\n=== 5/9 영상 생성 ===")
    clips = generate_clips(frames, script, output_dir, quality=quality)

    # 7. TTS 나레이션
    print("\n=== 6/9 TTS 나레이션 ===")
    narration = generate_narration(script, output_dir)
    if narration:
        print(f"나레이션: {narration['duration']:.1f}초")
    else:
        print("나레이션 생성 실패. 나레이션 없이 계속 진행.")

    # 8. Remotion 합성
    if clips:
        print("\n=== 7/9 Remotion 합성 ===")
        final = remotion_render(script, clips, narration, output_dir)
        if not final:
            print("Remotion 실패. FFmpeg 폴백...")
            final = concat_clips(clips, output_dir)

    # SEO
    print("\n=== 8/9 SEO 패키지 ===")
    _generate_seo_and_save(script, output_dir)

    print(f"\n=== 9/9 완료 ===")
    print(f"전체 파이프라인 완료! 출력: {output_dir}")

    # 업로드
    if args.upload:
        privacy = "public" if args.public else "private"
        cmd_upload_dir(str(output_dir), privacy)


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Shorts 자동화 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
사용 예시:
  python main.py                        전체 파이프라인 (대화형)
  python main.py --auto --upload        자동 선택 + 비공개 업로드
  python main.py --upload --public      업로드 (공개)
  python main.py --quality full         고품질 Veo 사용
  python main.py trends                 트렌드 수집만
  python main.py generate --topic "K8s" 특정 주제로 생성
  python main.py upload --dir outputs/  기존 영상 업로드
""",
    )

    # 공통 옵션
    parser.add_argument("--auto", action="store_true", help="자동 모드 (확인 없이 진행)")
    parser.add_argument("--upload", action="store_true", help="완료 후 YouTube 업로드")
    parser.add_argument("--public", action="store_true", help="공개 업로드 (기본: 비공개)")
    parser.add_argument(
        "--quality", choices=["fast", "full"], default="fast",
        help="Veo 품질 (fast=$0.10/s, full=$0.30/s)",
    )

    subparsers = parser.add_subparsers(dest="command")

    # trends 서브커맨드
    p_trends = subparsers.add_parser("trends", help="트렌드 수집만")
    p_trends.add_argument("--output", default="trends.json")
    p_trends.add_argument("--top", type=int, default=10)

    # generate 서브커맨드
    p_gen = subparsers.add_parser("generate", help="특정 주제로 콘텐츠 생성")
    p_gen.add_argument("--topic", required=True, help="주제")

    # upload 서브커맨드
    p_upload = subparsers.add_parser("upload", help="기존 영상 업로드")
    p_upload.add_argument("--dir", required=True, help="출력 디렉토리 경로")

    args = parser.parse_args()

    if args.command == "trends":
        cmd_trends(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "upload":
        cmd_upload(args)
    else:
        cmd_full_pipeline(args)


if __name__ == "__main__":
    main()
