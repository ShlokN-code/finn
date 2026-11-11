// Tiny inline sparkline (SVG). Values are plotted as given; no maths beyond scaling to the box.
export function Sparkline({
  values,
  width = 96,
  height = 24,
  className = "",
}: {
  values: (number | null)[];
  width?: number;
  height?: number;
  className?: string;
}) {
  const pts = values.map((v, i) => [i, v] as const).filter((p): p is readonly [number, number] => p[1] !== null);
  if (pts.length < 2) return null;
  const ys = pts.map((p) => p[1]);
  const lo = Math.min(...ys);
  const hi = Math.max(...ys);
  const span = hi - lo || 1;
  const n = values.length - 1 || 1;
  const xy = pts.map(([i, v]) => [(i / n) * (width - 2) + 1, height - 1 - ((v - lo) / span) * (height - 2)] as const);
  const d = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [lx, ly] = xy[xy.length - 1];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden className={`shrink-0 overflow-visible ${className}`}>
      <path d={d} fill="none" stroke="currentColor" strokeWidth={1.25} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r={1.75} fill="currentColor" />
    </svg>
  );
}
