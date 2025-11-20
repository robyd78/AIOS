import * as THREE from 'three';

export const clock = new THREE.Clock();
let rafId: number | null = null;

export function startLoop(
  update: (t: number, dt: number) => void,
  renderer: THREE.WebGLRenderer,
  scene: THREE.Scene,
  camera: THREE.Camera
) {
  stopLoop();
  clock.getDelta();
  const loop = (t: number) => {
    const dt = clock.getDelta();
    update(t, dt);
    renderer.render(scene, camera);
    rafId = requestAnimationFrame(loop);
  };
  rafId = requestAnimationFrame(loop);
}

export function stopLoop() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
}
