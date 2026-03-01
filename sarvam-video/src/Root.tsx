import React from "react";
import { Composition } from "remotion";
import { SarvamDemo } from "./compositions/SarvamDemo";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="SarvamDemo"
        component={SarvamDemo}
        durationInFrames={1080} // 36 seconds @ 30fps
        fps={30}
        width={1920}
        height={1080} // 16:9 landscape
      />
    </>
  );
};
