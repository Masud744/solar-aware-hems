import { useEffect, useRef } from 'react';
import { DataHonestyTag } from '../common/DataHonestyTag';
import type { DeviceStatus, SensorReading, LoadSource } from '../../types';

function getLoadSource(reading: SensorReading | null, status: DeviceStatus | null, key: string): LoadSource {
  const relayMap = reading?.relay_commanded_state || {};
  const r = (relayMap as any)[key];
  const applied = (typeof r === 'object' && r !== null ? r.applied_source : r) || (status as any)?.[key] || 'off';
  const s = String(applied).toLowerCase();
  if (s === 'grid' || s === 'solar' || s === 'off') return s as LoadSource;
  return 'off';
}

interface EnergyFlowProps {
  deviceStatus: DeviceStatus | null;
  reading: SensorReading | null;
}

/** Signature energy flow visualization — animated routing state. */
export function EnergyFlow({ deviceStatus, reading }: EnergyFlowProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);

  const hasGrid = ['load_1', 'load_2', 'load_3', 'load_4'].some(k => getLoadSource(reading, deviceStatus, k) === 'grid');
  const hasSolar = ['load_1', 'load_2', 'load_3', 'load_4'].some(k => getLoadSource(reading, deviceStatus, k) === 'solar');
  const loads = ['load_1', 'load_2', 'load_3', 'load_4'].map(k => ({ key: k, source: getLoadSource(reading, deviceStatus, k) }));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;

    function setup() {
      const rect = canvas!.getBoundingClientRect();
      canvas!.width = rect.width * dpr;
      canvas!.height = rect.height * dpr;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      return { w: rect.width, h: rect.height };
    }

    let { w, h } = setup();

    // Color tokens
    const getColor = (prop: string, fallback: string) =>
      getComputedStyle(document.documentElement).getPropertyValue(prop).trim() || fallback;

    function resolveColors() {
      return {
        solar: getColor('--solar', '#E8A317'),
        grid: getColor('--grid-accent', '#6B8CAE'),
        off: getColor('--text-3', '#555'),
        primary: getColor('--solar', '#E8A317'),
        text: getColor('--text-3', '#888'),
        border: getColor('--border', '#333'),
        bg: getColor('--glass', 'rgba(255,255,255,0.04)'),
      };
    }

    let colors = resolveColors();

    // Node positions
    function nodePositions() {
      return {
        grid: { x: w * 0.18, y: 40 },
        solar: { x: w * 0.82, y: 40 },
        home: { x: w * 0.5, y: h * 0.42 },
        loads: loads.map((_, i) => ({ x: w * (0.13 + 0.74 * i / 3), y: h - 40 })),
      };
    }

    let nodes = nodePositions();

    function buildParticles() {
      const p: Particle[] = [];
      if (hasGrid) for (let i = 0; i < 5; i++) p.push(mkParticle(nodes.grid, nodes.home, 'grid', i * 0.2));
      if (hasSolar) for (let i = 0; i < 5; i++) p.push(mkParticle(nodes.solar, nodes.home, 'solar', i * 0.2));
      loads.forEach((ld, i) => {
        if (ld.source !== 'off') for (let j = 0; j < 3; j++) p.push(mkParticle(nodes.home, nodes.loads[i], ld.source, j * 0.33));
      });
      return p;
    }

    particlesRef.current = buildParticles();

    function srcColor(src: string) {
      return src === 'solar' ? colors.solar : src === 'grid' ? colors.grid : colors.off;
    }

    function drawCurve(from: Pos, to: Pos, active: boolean, src: string) {
      ctx!.beginPath();
      const midY = (from.y + to.y) / 2;
      ctx!.moveTo(from.x, from.y);
      ctx!.quadraticCurveTo(from.x, midY, to.x, to.y);
      ctx!.strokeStyle = active ? srcColor(src) : colors.border;
      ctx!.lineWidth = active ? 1.5 : 0.5;
      ctx!.globalAlpha = active ? 0.3 : 0.08;
      ctx!.stroke();
      ctx!.globalAlpha = 1;
    }

    function drawNode(pos: Pos, label: string, src: string, size: number) {
      const c = srcColor(src);
      // Glow
      if (src !== 'off') {
        ctx!.beginPath();
        ctx!.arc(pos.x, pos.y, size * 0.8, 0, Math.PI * 2);
        ctx!.fillStyle = c;
        ctx!.globalAlpha = 0.06;
        ctx!.fill();
        ctx!.globalAlpha = 1;
      }
      // Circle
      ctx!.beginPath();
      ctx!.arc(pos.x, pos.y, size / 2, 0, Math.PI * 2);
      ctx!.fillStyle = colors.bg;
      ctx!.fill();
      ctx!.strokeStyle = src === 'off' ? colors.border : c;
      ctx!.lineWidth = src === 'off' ? 0.5 : 1.5;
      ctx!.globalAlpha = src === 'off' ? 0.3 : 0.7;
      ctx!.stroke();
      ctx!.globalAlpha = 1;
      // Label
      ctx!.fillStyle = colors.text;
      ctx!.font = '500 9px Inter, sans-serif';
      ctx!.textAlign = 'center';
      ctx!.fillText(label.toUpperCase(), pos.x, pos.y + size / 2 + 14);
    }

    function animate() {
      ctx!.clearRect(0, 0, w, h);

      // Paths
      drawCurve(nodes.grid, nodes.home, hasGrid, 'grid');
      drawCurve(nodes.solar, nodes.home, hasSolar, 'solar');
      loads.forEach((ld, i) => drawCurve(nodes.home, nodes.loads[i], ld.source !== 'off', ld.source));

      // Particles
      particlesRef.current.forEach(p => {
        p.t = (p.t + 0.005) % 1;
        const midY = (p.from.y + p.to.y) / 2;
        const mt = 1 - p.t;
        const px = mt * mt * p.from.x + 2 * mt * p.t * p.from.x + p.t * p.t * p.to.x;
        const py = mt * mt * p.from.y + 2 * mt * p.t * midY + p.t * p.t * p.to.y;
        ctx!.beginPath();
        ctx!.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx!.fillStyle = srcColor(p.source);
        ctx!.globalAlpha = 0.7 * Math.sin(p.t * Math.PI);
        ctx!.fill();
        ctx!.globalAlpha = 1;
      });

      // Source nodes
      drawNode(nodes.grid, 'Grid', hasGrid ? 'grid' : 'off', 40);
      drawNode(nodes.solar, 'Solar', hasSolar ? 'solar' : 'off', 40);

      // Home node
      const hSize = 48;
      ctx!.beginPath();
      ctx!.arc(nodes.home.x, nodes.home.y, hSize / 2, 0, Math.PI * 2);
      ctx!.fillStyle = colors.primary;
      ctx!.globalAlpha = 0.15;
      ctx!.fill();
      ctx!.globalAlpha = 1;
      ctx!.beginPath();
      ctx!.arc(nodes.home.x, nodes.home.y, hSize / 2 - 2, 0, Math.PI * 2);
      ctx!.fillStyle = colors.primary;
      ctx!.globalAlpha = 0.9;
      ctx!.fill();
      ctx!.globalAlpha = 1;
      ctx!.fillStyle = '#fff';
      ctx!.font = '600 16px Inter, sans-serif';
      ctx!.textAlign = 'center';
      ctx!.textBaseline = 'middle';
      ctx!.fillText('⌂', nodes.home.x, nodes.home.y);
      ctx!.textBaseline = 'alphabetic';
      ctx!.fillStyle = colors.text;
      ctx!.font = '500 9px Inter, sans-serif';
      ctx!.fillText('HOME', nodes.home.x, nodes.home.y + hSize / 2 + 14);

      // Load nodes
      loads.forEach((ld, i) => drawNode(nodes.loads[i], `L${i + 1}`, ld.source, 32));

      animRef.current = requestAnimationFrame(animate);
    }

    animate();

    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(animRef.current);
      ({ w, h } = setup());
      nodes = nodePositions();
      particlesRef.current = buildParticles();
      animate();
    });
    ro.observe(canvas);

    const mo = new MutationObserver(() => {
      cancelAnimationFrame(animRef.current);
      colors = resolveColors();
      animate();
    });
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    return () => { cancelAnimationFrame(animRef.current); ro.disconnect(); mo.disconnect(); };
  }, [deviceStatus, hasGrid, hasSolar, reading]);

  return (
    <div className="flow-wrap glass">
      <div className="sect-head" style={{ marginBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="sect-label">Energy Flow</span>
          <DataHonestyTag type="CALCULATED" size="sm" tooltip="Animated energy flow derived from authoritative relay routing" />
        </div>
        <span className="sect-sublabel">Dual-bank relay routing</span>
      </div>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: 280 }}
        aria-label="Energy flow visualization showing grid and solar routing to home loads"
        role="img"
      />
    </div>
  );
}

type Pos = { x: number; y: number };
interface Particle { from: Pos; to: Pos; source: string; t: number; }
function mkParticle(from: Pos, to: Pos, source: string, offset: number): Particle {
  return { from, to, source, t: offset };
}
