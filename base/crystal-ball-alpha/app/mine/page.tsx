'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// ─── API ──────────────────────────────────────────────────────
async function cbApi(input: string) {
    const res = await fetch('/api/mine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input }),
    });
    return res.json();
}

// ─── Types — from mine.ts KnownPoint + ConfigPoint ────────────
interface KnownPoint {
    x: number;
    y: number;
    coordinate: string;
    encoded: string;
    status: 'valid' | 'adjacent' | 'invalid';
    fromKernel: string;
    label: string;
    heat: number;
    depth: number;
    choices?: Array<{ dim: string; choice: string; childIdx: number }>;
    configLabel?: string;
}

// ─── Main ─────────────────────────────────────────────────────
export default function MinePage() {
    const [spaces, setSpaces] = useState<string[]>([]);
    const [spaceName, setSpaceName] = useState('');
    const [points, setPoints] = useState<KnownPoint[]>([]);
    const [selected, setSelected] = useState<KnownPoint | null>(null);
    const [hovered, setHovered] = useState<KnownPoint | null>(null);
    const [loading, setLoading] = useState(false);
    const [spaceInput, setSpaceInput] = useState('');
    const [mineInfo, setMineInfo] = useState('');

    // Viewport
    const [zoom, setZoom] = useState(1);
    const [panX, setPanX] = useState(0);
    const [panY, setPanY] = useState(0);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const isPanning = useRef(false);
    const lastMouse = useRef({ x: 0, y: 0 });
    const didDrag = useRef(false);

    // Load space list
    useEffect(() => {
        cbApi('list').then(data => {
            const s = data?.data?.spaces;
            if (Array.isArray(s)) setSpaces(s.map((x: any) => typeof x === 'string' ? x : x.name));
        }).catch(() => { });
    }, []);

    // Load space — read the mineSpace KnownPoints (now with labels, heat, depth)
    const loadSpace = useCallback(async (name: string) => {
        setLoading(true);
        setSelected(null);
        setHovered(null);
        setSpaceName(name);

        try {
            await cbApi(name);           // Enter space
            const mineData = await cbApi('mine');  // Compute configurations
            const ms = mineData?.data?.mineSpace || mineData?.data || {};
            const known: KnownPoint[] = ms?.known || [];
            setPoints(known);
            setMineInfo(mineData?.view || '');

            // Fit view — delay for canvas sizing
            requestAnimationFrame(() => {
                const canvas = canvasRef.current;
                if (known.length > 0 && canvas) {
                    const cw = canvas.clientWidth || 800;
                    const ch = canvas.clientHeight || 600;
                    const pad = 50;
                    const xs = known.map(p => p.x);
                    const ys = known.map(p => p.y);
                    const minX = Math.min(...xs);
                    const maxX = Math.max(...xs);
                    const minY = Math.min(...ys);
                    const maxY = Math.max(...ys);
                    const spanX = maxX - minX || 1;
                    const spanY = maxY - minY || 1;
                    const fitZoom = Math.min((cw - pad * 2) / spanX, (ch - pad * 2) / spanY);
                    setZoom(fitZoom);
                    setPanX(pad + (cw - pad * 2) / 2 - ((minX + maxX) / 2) * fitZoom);
                    setPanY(pad + (ch - pad * 2) / 2 - ((minY + maxY) / 2) * fitZoom);
                }
            });
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
    }, []);

    // Draw
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const dpr = window.devicePixelRatio || 1;
        const cw = canvas.clientWidth;
        const ch = canvas.clientHeight;
        canvas.width = cw * dpr;
        canvas.height = ch * dpr;
        ctx.scale(dpr, dpr);

        ctx.fillStyle = '#06060f';
        ctx.fillRect(0, 0, cw, ch);

        // Grid
        ctx.strokeStyle = 'rgba(100, 120, 255, 0.04)';
        ctx.lineWidth = 1;
        const gridStep = zoom * 0.1;
        if (gridStep > 15) {
            const startX = panX % gridStep;
            const startY = panY % gridStep;
            for (let x = startX; x < cw; x += gridStep) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, ch); ctx.stroke(); }
            for (let y = startY; y < ch; y += gridStep) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(cw, y); ctx.stroke(); }
        }

        // Points — draw adjacent first (behind), then valid (on top)
        const sorted = [...points].sort((a, b) => {
            if (a.status === 'adjacent' && b.status !== 'adjacent') return -1;
            if (a.status !== 'adjacent' && b.status === 'adjacent') return 1;
            return 0;
        });

        for (const p of sorted) {
            const sx = p.x * zoom + panX;
            const sy = p.y * zoom + panY;
            if (sx < -30 || sx > cw + 30 || sy < -30 || sy > ch + 30) continue;

            const isSelected = selected?.encoded === p.encoded;
            const isHovered = hovered?.encoded === p.encoded;
            const isFrozen = p.heat < 0.05;
            const isLocked = p.heat < 0.15;

            // Size by depth and status
            let r = p.status === 'adjacent' ? 3 : p.depth === 1 ? 6 : 5;
            if (isSelected) r = 8;
            if (isHovered) r = 7;

            // Glow
            if (isSelected || isHovered) {
                const grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 3);
                grad.addColorStop(0, isSelected ? 'rgba(0, 255, 180, 0.35)' : 'rgba(100, 180, 255, 0.25)');
                grad.addColorStop(1, 'transparent');
                ctx.fillStyle = grad;
                ctx.beginPath(); ctx.arc(sx, sy, r * 3, 0, Math.PI * 2); ctx.fill();
            }

            // Color: frozen=cyan, locked=purple, hot=orange, adjacent=dim
            let color: string;
            if (isSelected) color = '#00ffb4';
            else if (isHovered) color = '#64b4ff';
            else if (p.status === 'adjacent') color = 'rgba(245, 158, 11, 0.25)';
            else if (isFrozen) color = '#22d3ee';  // cyan = frozen/proven
            else if (isLocked) color = '#a78bfa';   // purple = locked
            else color = `hsl(${30 + p.heat * 20}, 80%, ${40 + p.heat * 15}%)`;  // warm orange

            ctx.fillStyle = color;
            ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.fill();

            // Ring for depth-1 nodes (dimensions)
            if (p.depth === 1 && p.status === 'valid') {
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.5;
                ctx.beginPath(); ctx.arc(sx, sy, r + 3, 0, Math.PI * 2); ctx.stroke();
            }

            // Label
            const showLabel = zoom > 200 || isSelected || isHovered || (p.depth === 1 && zoom > 80);
            if (showLabel && p.status === 'valid') {
                const fontSize = Math.min(12, Math.max(8, zoom / 60));
                ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
                ctx.textAlign = 'center';
                ctx.fillStyle = isSelected ? '#00ffb4' : isHovered ? '#e2e8f0' : 'rgba(200, 210, 255, 0.7)';
                ctx.fillText(p.label, sx, sy - r - 5);
            }

            // Encoding at high zoom
            if (zoom > 400 || isSelected) {
                ctx.font = `${Math.min(9, zoom / 80)}px monospace`;
                ctx.textAlign = 'center';
                ctx.fillStyle = 'rgba(100, 120, 180, 0.5)';
                ctx.fillText(`0.${p.encoded}`, sx, sy + r + 12);
            }
        }

        // Status bar
        ctx.font = '11px Inter, system-ui, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillStyle = 'rgba(255,255,255,0.25)';
        const valid = points.filter(p => p.status === 'valid').length;
        const adj = points.filter(p => p.status === 'adjacent').length;
        ctx.fillText(`${points.length} known  ·  ${valid} valid  ·  ${adj} adjacent  ·  zoom: ${zoom.toFixed(0)}`, 10, ch - 10);

    }, [points, zoom, panX, panY, selected, hovered]);

    // Hit test
    const getPointAtMouse = useCallback((e: React.MouseEvent): KnownPoint | null => {
        if (!canvasRef.current) return null;
        const rect = canvasRef.current.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        let closest: KnownPoint | null = null;
        let minD = Infinity;
        for (const p of points) {
            const sx = p.x * zoom + panX;
            const sy = p.y * zoom + panY;
            const d = Math.sqrt((mx - sx) ** 2 + (my - sy) ** 2);
            if (d < 18 && d < minD) { closest = p; minD = d; }
        }
        return closest;
    }, [points, zoom, panX, panY]);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        isPanning.current = true; didDrag.current = false;
        lastMouse.current = { x: e.clientX, y: e.clientY };
    }, []);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (isPanning.current) {
            const dx = e.clientX - lastMouse.current.x;
            const dy = e.clientY - lastMouse.current.y;
            if (Math.abs(dx) > 2 || Math.abs(dy) > 2) didDrag.current = true;
            setPanX(p => p + dx); setPanY(p => p + dy);
            lastMouse.current = { x: e.clientX, y: e.clientY };
        } else {
            setHovered(getPointAtMouse(e));
        }
    }, [getPointAtMouse]);

    const handleMouseUp = useCallback((e: React.MouseEvent) => {
        if (!didDrag.current) { const pt = getPointAtMouse(e); if (pt) setSelected(pt); }
        isPanning.current = false;
    }, [getPointAtMouse]);

    const handleWheel = useCallback((e: React.WheelEvent) => {
        e.preventDefault();
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
        const newZoom = Math.max(10, Math.min(50000, zoom * factor));
        setPanX(p => mx - (mx - p) * (newZoom / zoom));
        setPanY(p => my - (my - p) * (newZoom / zoom));
        setZoom(newZoom);
    }, [zoom]);

    // Get nearby points (same depth or ±1 coordinate segment)
    const getNearby = useCallback((p: KnownPoint): KnownPoint[] => {
        if (!p) return [];
        const parts = p.coordinate.split('.');
        return points.filter(q => {
            if (q.encoded === p.encoded) return false;
            const qParts = q.coordinate.split('.');
            // Same parent (share all but last segment)
            if (parts.length === qParts.length && parts.length > 1) {
                return parts.slice(0, -1).join('.') === qParts.slice(0, -1).join('.');
            }
            // Same depth-1 group
            if (parts.length === 1 && qParts.length === 1) return true;
            return false;
        });
    }, [points]);

    return (
        <div style={{ height: '100vh', background: '#06060f', color: '#e2e8f0', fontFamily: '"Inter", system-ui, sans-serif', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div style={{ padding: '10px 20px', borderBottom: '1px solid rgba(100,120,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {spaceName && <button onClick={() => { setSpaceName(''); setPoints([]); setSelected(null); }} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 13 }}>← Back</button>}
                    <span style={{ fontSize: 16, fontWeight: 700, background: 'linear-gradient(135deg, #8b5cf6, #06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>⛏ MineSpace</span>
                    {spaceName && <span style={{ fontSize: 13, color: '#8b5cf6', fontWeight: 600 }}>{spaceName}</span>}
                </div>
                {spaceName && (
                    <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#475569' }}>
                        <span>🟣 locked</span>
                        <span style={{ color: '#22d3ee' }}>🔵 frozen</span>
                        <span style={{ color: '#f59e0b' }}>🟡 adjacent</span>
                    </div>
                )}
            </div>

            {/* Space selector */}
            {!spaceName && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
                    <h2 style={{ fontSize: 15, color: '#94a3b8', fontWeight: 400 }}>Choose a space</h2>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center', maxWidth: 700 }}>
                        {spaces.map(name => (
                            <button key={name} onClick={() => loadSpace(name)} style={{ padding: '6px 14px', fontSize: 12, borderRadius: 6, border: '1px solid rgba(139,92,246,0.2)', background: 'rgba(20,20,40,0.6)', color: '#c4b5fd', cursor: 'pointer' }}>{name}</button>
                        ))}
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                        <input value={spaceInput} onChange={e => setSpaceInput(e.target.value)} placeholder="Type a space name..."
                            style={{ padding: '6px 12px', fontSize: 12, borderRadius: 6, border: '1px solid rgba(100,120,255,0.2)', background: 'rgba(15,15,35,0.8)', color: '#e2e8f0', width: 200, outline: 'none' }}
                            onKeyDown={e => e.key === 'Enter' && spaceInput && loadSpace(spaceInput)} />
                        <button onClick={() => spaceInput && loadSpace(spaceInput)} style={{ padding: '6px 14px', fontSize: 12, borderRadius: 6, border: '1px solid #00ffb4', background: 'rgba(0,255,180,0.08)', color: '#00ffb4', cursor: 'pointer' }}>Go</button>
                    </div>
                </div>
            )}

            {/* Mine plane */}
            {spaceName && (
                <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    <div style={{ flex: 1, position: 'relative' }}>
                        {loading ? (
                            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569' }}>Loading...</div>
                        ) : (
                            <canvas ref={canvasRef}
                                style={{ width: '100%', height: '100%', cursor: hovered ? 'pointer' : 'crosshair' }}
                                onMouseDown={handleMouseDown} onMouseMove={handleMouseMove}
                                onMouseUp={handleMouseUp} onMouseLeave={() => { isPanning.current = false; setHovered(null); }}
                                onWheel={handleWheel} />
                        )}
                        {/* Hover tooltip */}
                        {hovered && (
                            <div style={{ position: 'absolute', top: 10, left: 10, pointerEvents: 'none', background: 'rgba(10,10,30,0.9)', border: '1px solid rgba(100,120,255,0.2)', borderRadius: 8, padding: '8px 12px', fontSize: 11, maxWidth: 300 }}>
                                <div style={{ fontWeight: 700, color: '#00ffb4', fontSize: 13 }}>{hovered.label}</div>
                                <div style={{ color: '#64748b', fontFamily: 'monospace', marginTop: 2 }}>0.{hovered.encoded}</div>
                                <div style={{ color: '#475569', marginTop: 2 }}>depth: {hovered.depth} · heat: {hovered.heat.toFixed(2)} · {hovered.status}</div>
                            </div>
                        )}
                    </div>

                    {/* Detail panel */}
                    <div style={{ width: 320, flexShrink: 0, borderLeft: '1px solid rgba(100,120,255,0.1)', padding: 16, overflowY: 'auto', background: 'rgba(8,8,20,0.8)' }}>
                        {selected ? (
                            <>
                                <div style={{ fontSize: 11, color: selected.status === 'valid' ? '#22d3ee' : '#f59e0b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
                                    {selected.status === 'valid' ? '★ Current Configuration' : `△ ${selected.label}`}
                                </div>
                                <div style={{ fontSize: 12, fontWeight: 600, color: '#a78bfa', fontFamily: 'monospace', marginBottom: 12 }}>
                                    ℝ = 0.{selected.encoded}
                                </div>

                                {/* Configuration choices */}
                                {selected.choices && selected.choices.length > 0 && (
                                    <div style={{ marginBottom: 16 }}>
                                        {selected.choices.map((c, i) => (
                                            <div key={i} style={{
                                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                                padding: '5px 8px', marginBottom: 2, borderRadius: 4,
                                                background: selected.status === 'valid' || selected.depth !== i + 1
                                                    ? 'rgba(30,30,60,0.4)' : 'rgba(139,92,246,0.15)',
                                                border: selected.depth === i + 1 ? '1px solid rgba(139,92,246,0.3)' : '1px solid transparent',
                                            }}>
                                                <span style={{ fontSize: 10, color: '#64748b' }}>{c.dim}</span>
                                                <span style={{
                                                    fontSize: 12, fontWeight: 600,
                                                    color: selected.depth === i + 1 ? '#f59e0b' : '#c4b5fd',
                                                }}>
                                                    {c.choice}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 12 }}>
                                    <div style={{ background: 'rgba(30,30,60,0.5)', borderRadius: 6, padding: 6 }}>
                                        <div style={{ fontSize: 9, color: '#475569' }}>Position</div>
                                        <div style={{ fontSize: 10, color: '#94a3b8', fontFamily: 'monospace' }}>({selected.x.toFixed(3)}, {selected.y.toFixed(3)})</div>
                                    </div>
                                    <div style={{ background: 'rgba(30,30,60,0.5)', borderRadius: 6, padding: 6 }}>
                                        <div style={{ fontSize: 9, color: '#475569' }}>Heat</div>
                                        <div style={{ fontSize: 10, color: selected.heat < 0.1 ? '#22d3ee' : '#f59e0b', fontWeight: 600 }}>{selected.heat.toFixed(2)}</div>
                                    </div>
                                </div>

                                <div style={{ fontSize: 10, color: '#475569', marginBottom: 12 }}>
                                    kernel: <span style={{ color: '#64748b' }}>{selected.fromKernel}</span>
                                </div>

                                {/* Adjacent configs */}
                                {(() => {
                                    const nearby = getNearby(selected);
                                    if (nearby.length === 0) return null;
                                    return (
                                        <div>
                                            <div style={{ fontSize: 10, color: '#475569', marginBottom: 6, borderTop: '1px solid rgba(100,120,255,0.1)', paddingTop: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                                Adjacent configs ({nearby.length})
                                            </div>
                                            {nearby.slice(0, 30).map(n => (
                                                <button key={n.encoded}
                                                    onClick={() => setSelected(n)}
                                                    style={{
                                                        display: 'block', width: '100%', textAlign: 'left',
                                                        background: 'rgba(30,30,60,0.3)', border: '1px solid rgba(100,120,255,0.08)',
                                                        borderRadius: 4, padding: '4px 8px', marginBottom: 2,
                                                        cursor: 'pointer', color: '#c4b5fd', fontSize: 11,
                                                    }}>
                                                    <span style={{ fontWeight: 600, color: '#f59e0b' }}>{n.label}</span>
                                                </button>
                                            ))}
                                        </div>
                                    );
                                })()}
                            </>
                        ) : (
                            <div style={{ color: '#475569', fontSize: 12 }}>
                                <p style={{ fontWeight: 600, color: '#64748b' }}>Click any point to inspect it.</p>
                                <p style={{ fontSize: 11, marginTop: 8, lineHeight: 1.5 }}>
                                    Each point is a complete <strong>configuration</strong> — a full selection across all dimensions.
                                    The center point is the current config. Adjacent points differ by one dimension choice.
                                </p>
                                {mineInfo && <pre style={{ marginTop: 16, fontSize: 10, color: '#334155', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{mineInfo}</pre>}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
