// Three.js Canvas isolated in its own module to dodge React 19 StrictMode
// double-mount issue with @react-three/fiber 9.6.1's applyProps reconciler.
// Loaded via React.lazy from PublicDemoPage so the second strict-mode mount
// never reaches Canvas internals.
import React, { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { DemoHouse } from "./viewer/ViewerScene";

const DemoCanvas = ({ faceStyle, hiddenLayers, resetKey }) => {
  return (
    <Canvas
      key={resetKey}
      camera={{ position: [12, 9, 14], fov: 50, near: 0.1, far: 2000 }}
      gl={{ antialias: true, localClippingEnabled: true }}
      dpr={[1, 2]}
      style={{ width: "100%", height: "100%", touchAction: "none" }}
      onCreated={({ gl }) => { gl.localClippingEnabled = true; }}
    >
      <color attach="background" args={["#0a0a0a"]} />
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 15, 8]} intensity={0.9} />
      <hemisphereLight args={[0xddeeff, 0x202020, 0.3]} />
      <Suspense fallback={null}>
        <DemoHouse
          faceStyle={faceStyle}
          hiddenLayers={hiddenLayers}
          onLayersDetected={() => {}}
          clippingPlanes={[]}
          onMeshClick={() => {}}
        />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
          <planeGeometry args={[40, 40]} />
          <meshStandardMaterial color={0x141414} roughness={0.95} />
        </mesh>
      </Suspense>
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} target={[0, 2, 0]} />
    </Canvas>
  );
};

export default DemoCanvas;
