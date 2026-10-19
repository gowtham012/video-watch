import React from "react";
import { Audio, Composition, Sequence, registerRoot, staticFile } from "remotion";
import { FPS, s } from "./theme";
import { S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11 } from "./Shots";

// [start, end] seconds — every boundary on a beat or half-beat at 120 bpm
const SHOTS: [number, number, React.FC][] = [
  [0, 4.4, S01], [4.4, 6.2, S02], [6.2, 10.0, S03], [10.0, 13.5, S04], [13.5, 14.8, S05], [14.8, 19.0, S06],
  [19.0, 21.0, S07], [21.0, 24.0, S08], [24.0, 25.0, S09], [25.0, 28.5, S10], [28.5, 33.0, S11],
];

const Ad: React.FC = () => (
  <>
    {SHOTS.map(([a, b, Shot], i) => (
      <Sequence key={i} from={s(a)} durationInFrames={s(b) - s(a)}>
        <Shot />
      </Sequence>
    ))}
    <Audio src={staticFile("music.wav")} />
  </>
);

registerRoot(() => <Composition id="Ad" component={Ad} durationInFrames={s(33)} fps={FPS} width={1920} height={1080} />);
