import { Composition, getInputProps, registerRoot } from "remotion";
import { ShortsVideo, type ShortsVideoProps } from "./ShortsVideo";

const FPS = 30;

const Root: React.FC = () => {
  const props = getInputProps() as ShortsVideoProps;
  const durationInFrames = props.totalDurationFrames || FPS * 60;

  return (
    <Composition
      id="ShortsVideo"
      component={ShortsVideo}
      durationInFrames={durationInFrames}
      fps={FPS}
      width={1080}
      height={1920}
      defaultProps={props}
    />
  );
};

registerRoot(Root);
