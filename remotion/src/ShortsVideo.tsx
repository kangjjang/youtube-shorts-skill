import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  OffthreadVideo,
  staticFile,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/NotoSansKR";

const { fontFamily } = loadFont();

export interface SceneData {
  clipFile: string;
  textOverlay: string;
  durationFrames: number;
}

export interface ShortsVideoProps {
  scenes: SceneData[];
  subtitles: string[];
  narrationFile: string;
  totalDurationFrames: number;
}

const SubtitleOverlay: React.FC<{ text: string }> = ({ text }) => (
  <div
    style={{
      position: "absolute",
      bottom: 160,
      left: 40,
      right: 40,
      display: "flex",
      justifyContent: "center",
    }}
  >
    <div
      style={{
        backgroundColor: "rgba(0, 0, 0, 0.7)",
        borderRadius: 12,
        padding: "16px 28px",
        maxWidth: "90%",
      }}
    >
      <span
        style={{
          fontFamily,
          fontSize: 48,
          fontWeight: 700,
          color: "#FFFFFF",
          textAlign: "center",
          lineHeight: 1.4,
          textShadow: "0 2px 8px rgba(0,0,0,0.5)",
        }}
      >
        {text}
      </span>
    </div>
  </div>
);

export const ShortsVideo: React.FC<ShortsVideoProps> = ({
  scenes,
  subtitles,
  narrationFile,
  totalDurationFrames,
}) => {
  const { fps } = useVideoConfig();

  // 자막 타이밍 계산: 전체 시간을 자막 수로 균등 분배
  const subtitleDuration =
    subtitles.length > 0
      ? Math.floor(totalDurationFrames / subtitles.length)
      : totalDurationFrames;

  // 씬 시작 프레임 누적 계산
  let sceneOffset = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {/* 배경 영상 클립 */}
      {scenes.map((scene, i) => {
        const from = sceneOffset;
        sceneOffset += scene.durationFrames;

        return (
          <Sequence
            key={`clip-${i}`}
            from={from}
            durationInFrames={scene.durationFrames}
          >
            <AbsoluteFill>
              <OffthreadVideo
                src={staticFile(scene.clipFile)}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                pauseWhenBuffering
              />
            </AbsoluteFill>

            {/* 텍스트 오버레이 (씬별) */}
            {scene.textOverlay && (
              <div
                style={{
                  position: "absolute",
                  top: 120,
                  left: 40,
                  right: 40,
                  display: "flex",
                  justifyContent: "center",
                }}
              >
                <span
                  style={{
                    fontFamily,
                    fontSize: 42,
                    fontWeight: 600,
                    color: "#00E5FF",
                    textAlign: "center",
                    textShadow:
                      "0 0 20px rgba(0,229,255,0.5), 0 2px 4px rgba(0,0,0,0.8)",
                  }}
                >
                  {scene.textOverlay}
                </span>
              </div>
            )}
          </Sequence>
        );
      })}

      {/* 자막 오버레이 */}
      {subtitles.map((sub, i) => (
        <Sequence
          key={`sub-${i}`}
          from={i * subtitleDuration}
          durationInFrames={subtitleDuration}
        >
          <SubtitleOverlay text={sub} />
        </Sequence>
      ))}

      {/* 나레이션 오디오 */}
      {narrationFile && (
        <Audio src={staticFile(narrationFile)} volume={1} />
      )}
    </AbsoluteFill>
  );
};
