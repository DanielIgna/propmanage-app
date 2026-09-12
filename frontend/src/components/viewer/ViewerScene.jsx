// Digital Twin viewer — scene primitives (DemoHouse, Model loader, ResetCamera).
import React, { useEffect, useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";

// Procedural demo house — primitive walls/slabs/doors/columns with semantic names.
export const DemoHouse = ({ faceStyle, hiddenLayers, onLayersDetected, clippingPlanes, onMeshClick }) => {
  useEffect(() => {
    onLayersDetected?.(["AR_PERETI", "AR_PLANSEE", "AR_STALPI", "AR_USI", "AR_FERESTRE", "AR_ACOPERIS"]);
  }, [onLayersDetected]);

  const elements = useMemo(() => [
    { layer: "AR_PLANSEE", name: "AR_PLANSEE_parter", position: [0, 0, 0], scale: [8, 0.2, 6], color: 0x9a8a72 },
    { layer: "AR_PLANSEE", name: "AR_PLANSEE_etaj", position: [0, 3, 0], scale: [8, 0.2, 6], color: 0x9a8a72 },
    { layer: "AR_ACOPERIS", name: "AR_ACOPERIS_principal", position: [0, 6.4, 0], scale: [9, 0.15, 7], color: 0x3a2a20 },
    { layer: "AR_PERETI", name: "AR_PERETI_nord_parter", position: [0, 1.5, -3], scale: [8, 3, 0.25], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_sud_parter", position: [0, 1.5, 3], scale: [8, 3, 0.25], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_est_parter", position: [4, 1.5, 0], scale: [0.25, 3, 6], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_vest_parter", position: [-4, 1.5, 0], scale: [0.25, 3, 6], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_nord_etaj", position: [0, 4.7, -3], scale: [8, 3, 0.25], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_sud_etaj", position: [0, 4.7, 3], scale: [8, 3, 0.25], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_est_etaj", position: [4, 4.7, 0], scale: [0.25, 3, 6], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_vest_etaj", position: [-4, 4.7, 0], scale: [0.25, 3, 6], color: 0xc8b89a },
    { layer: "AR_PERETI", name: "AR_PERETI_despartitor", position: [-1, 1.5, 0], scale: [0.15, 3, 6], color: 0xd8c8a6 },
    { layer: "AR_STALPI", name: "AR_STALPI_NV", position: [-3.7, 1.5, -2.7], scale: [0.3, 3, 0.3], color: 0x666666 },
    { layer: "AR_STALPI", name: "AR_STALPI_NE", position: [3.7, 1.5, -2.7], scale: [0.3, 3, 0.3], color: 0x666666 },
    { layer: "AR_STALPI", name: "AR_STALPI_SV", position: [-3.7, 1.5, 2.7], scale: [0.3, 3, 0.3], color: 0x666666 },
    { layer: "AR_STALPI", name: "AR_STALPI_SE", position: [3.7, 1.5, 2.7], scale: [0.3, 3, 0.3], color: 0x666666 },
    { layer: "AR_USI", name: "AR_USI_intrare", position: [2, 1.1, 3], scale: [1, 2.1, 0.1], color: 0x5a3a20 },
    { layer: "AR_USI", name: "AR_USI_interior_parter", position: [-1, 1.05, 1], scale: [0.1, 2.1, 0.85], color: 0x5a3a20 },
    { layer: "AR_FERESTRE", name: "AR_FERESTRE_S1", position: [-2, 1.7, 3], scale: [1.2, 1.2, 0.1], color: 0x6ab0d4 },
    { layer: "AR_FERESTRE", name: "AR_FERESTRE_S2", position: [-2, 4.8, 3], scale: [1.2, 1.2, 0.1], color: 0x6ab0d4 },
    { layer: "AR_FERESTRE", name: "AR_FERESTRE_E1", position: [4, 4.8, -1], scale: [0.1, 1.2, 1.2], color: 0x6ab0d4 },
    { layer: "AR_FERESTRE", name: "AR_FERESTRE_W1", position: [-4, 1.7, -1], scale: [0.1, 1.2, 1.2], color: 0x6ab0d4 },
  ], []);

  const renderMaterial = (color) => {
    const cp = clippingPlanes && clippingPlanes.length ? clippingPlanes : null;
    const common = { clippingPlanes: cp, side: THREE.DoubleSide };
    if (faceStyle === "wireframe") {
      return <meshBasicMaterial color={0x222222} wireframe {...common} />;
    }
    if (faceStyle === "white") {
      return <meshStandardMaterial color={0xf5f5f5} roughness={0.7} metalness={0.02} {...common} />;
    }
    if (faceStyle === "xray") {
      return (
        <meshStandardMaterial
          color={color}
          transparent
          opacity={0.18}
          depthWrite={false}
          {...common}
        />
      );
    }
    if (faceStyle === "monochrome") {
      return <meshStandardMaterial color={0x9a9a9a} roughness={0.85} {...common} />;
    }
    return <meshStandardMaterial color={color} roughness={0.55} metalness={0.05} {...common} />;
  };

  return (
    <group>
      {elements.map((el) => {
        if (hiddenLayers.has(el.layer)) return null;
        return (
          <mesh
            key={el.name}
            name={el.name}
            position={el.position}
            scale={el.scale}
            onClick={(e) => {
              e.stopPropagation();
              onMeshClick?.(e);
            }}
          >
            <boxGeometry args={[1, 1, 1]} />
            {renderMaterial(el.color)}
          </mesh>
        );
      })}
    </group>
  );
};

// Loaded scene wrapper — applies face style + collects layer info + clipping.
export const Model = ({ url, faceStyle, hiddenLayers, onLayersDetected, clippingPlanes }) => {
  const { scene } = useGLTF(url);
  const originalMaterials = useRef(new Map());

  useEffect(() => {
    const layers = new Set();
    scene.traverse((obj) => {
      if (obj.isMesh && obj.name) {
        const parts = obj.name.split(/[_./]/);
        if (parts.length >= 2 && /^[A-Z]/.test(parts[0])) {
          layers.add(`${parts[0]}_${parts[1]}`);
        } else if (obj.parent && obj.parent.name) {
          layers.add(obj.parent.name);
        }
      }
    });
    onLayersDetected?.(Array.from(layers).sort());
  }, [scene, onLayersDetected]);

  useEffect(() => {
    scene.traverse((obj) => {
      if (!obj.isMesh || !obj.material) return;
      if (!originalMaterials.current.has(obj.uuid)) {
        originalMaterials.current.set(obj.uuid, obj.material);
      }
      const orig = originalMaterials.current.get(obj.uuid);

      let mat;
      switch (faceStyle) {
        case "white":
          mat = new THREE.MeshStandardMaterial({ color: 0xf5f5f5, roughness: 0.7, metalness: 0.05 });
          break;
        case "xray":
          mat = new THREE.MeshStandardMaterial({
            color: 0x88aaff, transparent: true, opacity: 0.15, depthWrite: false, side: THREE.DoubleSide,
          });
          break;
        case "wireframe":
          mat = new THREE.MeshBasicMaterial({ color: 0x222222, wireframe: true });
          break;
        case "monochrome":
          mat = new THREE.MeshStandardMaterial({ color: 0x999999, roughness: 0.9 });
          break;
        case "shaded":
        default:
          mat = orig;
          break;
      }
      obj.material = mat;
      if (mat) {
        mat.clippingPlanes = clippingPlanes && clippingPlanes.length ? clippingPlanes : null;
        mat.clipShadows = true;
        mat.side = THREE.DoubleSide;
        mat.needsUpdate = true;
      }
    });
  }, [scene, faceStyle, clippingPlanes]);

  useEffect(() => {
    scene.traverse((obj) => {
      if (!obj.isMesh || !obj.name) return;
      const parts = obj.name.split(/[_./]/);
      const layerKey = parts.length >= 2 && /^[A-Z]/.test(parts[0]) ? `${parts[0]}_${parts[1]}` : obj.parent?.name;
      obj.visible = !hiddenLayers.has(layerKey);
    });
  }, [scene, hiddenLayers]);

  return <primitive object={scene} />;
};

// Wraps a real glb model with a transparent click-catcher.
export const ModelWithEvents = ({ url, faceStyle, hiddenLayers, onLayersDetected, clippingPlanes, onMeshClick }) => (
  <group
    onClick={(e) => {
      e.stopPropagation();
      onMeshClick?.(e);
    }}
  >
    <Model
      url={url}
      faceStyle={faceStyle}
      hiddenLayers={hiddenLayers}
      onLayersDetected={onLayersDetected}
      clippingPlanes={clippingPlanes}
    />
  </group>
);

export const ResetCamera = ({ resetTrigger }) => {
  const { camera, controls } = useThree();
  useEffect(() => {
    if (resetTrigger === 0) return;
    camera.position.set(8, 6, 10);
    camera.lookAt(0, 1, 0);
    controls?.reset?.();
  }, [resetTrigger, camera, controls]);
  return null;
};


// ============= MULTI-LAYER SCENE =============
// Loads multiple GLB models simultaneously, each treated as an independent
// building system (structure / electric / plumbing / hvac / ...). The
// LayerPanel toggles visibility + opacity per layer — this is the "glass
// walls X-Ray" experience requested by the user.
//
// Props:
//   layers: [
//     { id, url, label, color (hex 0x..), opacity (0-1), visible (bool) }
//   ]
//   clippingPlanes: THREE.Plane[] | null
//
// Each layer keeps its raw geometry but its material is rebuilt with the
// layer's colour + opacity + transparency. Setting opacity=1 + transparent=false
// renders fully opaque (structure default). Setting opacity=0.25 renders glass.
const LayerModel = ({ layer, clippingPlanes }) => {
  const { scene } = useGLTF(layer.url);
  // Clone so multiple instances of the same URL keep independent materials.
  const cloned = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    cloned.traverse((obj) => {
      if (!obj.isMesh) return;
      const isTransparent = layer.opacity < 1.0;
      const mat = new THREE.MeshStandardMaterial({
        color: layer.color,
        roughness: 0.55,
        metalness: 0.05,
        transparent: isTransparent,
        opacity: layer.opacity,
        depthWrite: !isTransparent, // transparent layers shouldn't occlude what's behind
        side: THREE.DoubleSide,
      });
      mat.clippingPlanes = clippingPlanes && clippingPlanes.length ? clippingPlanes : null;
      mat.clipShadows = true;
      mat.needsUpdate = true;
      obj.material = mat;
      obj.castShadow = !isTransparent;
      obj.receiveShadow = !isTransparent;
    });
  }, [cloned, layer.color, layer.opacity, clippingPlanes]);

  if (!layer.visible) return null;
  return <primitive object={cloned} />;
};


export const MultiLayerScene = ({ layers, clippingPlanes, onMeshClick }) => {
  // Render order: opaque first (structure, walls), then transparent overlays
  // (electric, plumbing, hvac). Three.js sorts by depth but ordering helps.
  const sorted = useMemo(() => {
    return [...layers].sort((a, b) => (b.opacity || 0) - (a.opacity || 0));
  }, [layers]);
  return (
    <group
      onClick={(e) => {
        e.stopPropagation();
        onMeshClick?.(e);
      }}
    >
      {sorted.map((layer) => (
        <LayerModel key={layer.id} layer={layer} clippingPlanes={clippingPlanes} />
      ))}
    </group>
  );
};
