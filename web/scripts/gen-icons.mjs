// PWA icons from one SVG (no font dependency: the F is drawn with rectangles). Run: node scripts/gen-icons.mjs
import sharp from "sharp";

const ink = "#16150f";
const paper = "#f7f6f2";
// pad = safe-zone margin for maskable icons (Android crops to a circle/squircle)
const svg = (pad) => {
  const s = 512, a = pad, w = s - 2 * pad, u = w / 10;
  const x = a + 3.2 * u, y = a + 2.2 * u;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}">
  <rect width="${s}" height="${s}" fill="${ink}" ${pad ? "" : `rx="${s * 0.22}"`}/>
  <rect x="${x}" y="${y}" width="${1.3 * u}" height="${5.6 * u}" fill="${paper}"/>
  <rect x="${x}" y="${y}" width="${4.0 * u}" height="${1.2 * u}" fill="${paper}"/>
  <rect x="${x}" y="${y + 2.5 * u}" width="${3.1 * u}" height="${1.1 * u}" fill="${paper}"/>
  <rect x="${x + 4.6 * u}" y="${y + 4.6 * u}" width="${1.0 * u}" height="${1.0 * u}" fill="#c9a227"/>
</svg>`;
};

const out = [
  ["public/icons/icon-192.png", 192, 0],
  ["public/icons/icon-512.png", 512, 0],
  ["public/icons/maskable-512.png", 512, 72],
  ["public/icons/apple-touch-icon.png", 180, 40],
];
for (const [file, size, pad] of out) {
  await sharp(Buffer.from(svg(pad))).resize(size, size).png().toFile(file);
  console.log("wrote", file);
}
