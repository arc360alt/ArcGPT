// blobs.js - Animated SVG/Canvas blobs for background

// This script draws animated, morphing blobs on a canvas with a blue-tinted theme.
// You can tweak the color stops and number/size of blobs if you want.

(function() {
  const canvas = document.getElementById('blob-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width = window.innerWidth;
  let height = window.innerHeight;
  let dpr = window.devicePixelRatio || 1;

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
  }
  resize();
  window.addEventListener('resize', resize);

  // Blob configuration
  const blobs = [
    {
      baseX: 0.25, baseY: 0.4, r: 330,
      colorStops: [
        { stop: 0, color: "rgba(24, 178, 255, 0.16)" },
        { stop: 1, color: "rgba(0, 69, 255, 0.05)" }
      ],
      speed: 2.5,
      offset: 0,
      phase: 0
    },
    {
      baseX: 0.7, baseY: 0.25, r: 230,
      colorStops: [
        { stop: 0, color: "rgba(23, 255, 221, 0.11)" },
        { stop: 1, color: "rgba(0, 69, 255, 0.01)" }
      ],
      speed: 1.2,
      offset: 5,
      phase: 1.8
    },
    {
      baseX: 0.75, baseY: 0.85, r: 170,
      colorStops: [
        { stop: 0, color: "rgba(0, 186, 255, 0.13)" },
        { stop: 1, color: "rgba(0, 69, 255, 0.01)" }
      ],
      speed: 1.8,
      offset: 8.3,
      phase: 3.3
    }
  ];

  function drawBlob(blob, time) {
    // Animate center
    const x = blob.baseX * width + Math.sin(time / (6.5 + blob.offset) + blob.phase) * 48;
    const y = blob.baseY * height + Math.cos(time / (4.3 + blob.offset) + blob.phase) * 48;

    // Animate radius
    const r = blob.r + Math.sin(time / (2.1 + blob.offset) + blob.phase) * 32;

    // Draw radial gradient blob
    const grad = ctx.createRadialGradient(x, y, r * 0.35, x, y, r);
    for (const stop of blob.colorStops) {
      grad.addColorStop(stop.stop, stop.color);
    }
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.globalAlpha = 1;
    ctx.fill();
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);
    const now = Date.now() / 1000;
    blobs.forEach(blob => drawBlob(blob, now * blob.speed));
    requestAnimationFrame(animate);
  }

  animate();
})();