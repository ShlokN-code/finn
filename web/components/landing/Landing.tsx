// Desktop landing: what FINN is, a live phone-frame preview of the real app, and a QR to open it on a phone.
// Server component; the QR is rendered to SVG at build time (no client JS).
import { renderSVG } from "uqr";

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://finn-tau-red.vercel.app").replace(/\/$/, "");

const POINTS = [
  { k: "Default to silence", v: "Routine filings are hidden. You see the few that change your view, ranked." },
  { k: "Show the proof", v: "Every number opens its filing, page and quote. Unverifiable means it says so." },
  { k: "Hold management to it", v: "The Promise Ledger scores what management said against what they delivered." },
];

export function Landing() {
  const qr = renderSVG(SITE_URL, { border: 1, pixelSize: 6, whiteColor: "#ffffff", blackColor: "#16150f" });
  return (
    <main className="mx-auto flex min-h-dvh max-w-[1160px] items-center gap-16 px-12 py-12">
      <section className="min-w-0 flex-1">
        <p className="t-micro text-ink-3">FINN · Indian equities · NSE</p>
        <h1 className="mt-4 font-serif text-[56px] font-medium leading-[60px] tracking-[-0.02em]">
          Your portfolio&apos;s editor.
        </h1>
        <p className="mt-5 max-w-[520px] font-serif text-[22px] leading-[31px] text-ink-2">
          FINN reads every filing, price move and transcript, and shows you only what changes your view — with proof.
        </p>
        <dl className="mt-10 max-w-[560px] divide-y divide-rule border-y border-rule">
          {POINTS.map((p) => (
            <div key={p.k} className="grid grid-cols-[180px_1fr] gap-6 py-4">
              <dt className="text-[15px] font-semibold">{p.k}</dt>
              <dd className="text-[15px] text-ink-2">{p.v}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-10 flex items-center gap-6">
          <div
            className="size-[132px] shrink-0 overflow-hidden rounded-lg border border-rule bg-white p-1.5"
            role="img"
            aria-label={`QR code for ${SITE_URL}`}
            dangerouslySetInnerHTML={{ __html: qr }}
          />
          <div>
            <p className="t-headline">Open on your phone</p>
            <p className="t-small mt-1 max-w-[300px] text-ink-2">
              Built for one hand and thirty seconds. No login — a demo portfolio of 18 NSE stocks is loaded.
            </p>
            <p className="t-small mt-2 font-mono text-ink-3">{SITE_URL.replace(/^https:\/\//, "")}</p>
          </div>
        </div>
      </section>
      <section aria-label="Live preview" className="shrink-0">
        <div className="relative h-[min(812px,calc(100dvh-110px))] min-h-[560px] w-[390px] rounded-[54px] border border-rule bg-ink p-3 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.35)]">
          <div className="absolute left-1/2 top-5 z-10 h-[26px] w-[110px] -translate-x-1/2 rounded-full bg-ink" aria-hidden />
          <iframe
            src="/brief"
            title="FINN on a phone — live"
            className="h-full w-full rounded-[42px] bg-paper"
            loading="eager"
          />
        </div>
        <p className="t-small mt-3 text-center text-ink-3">Live — swipe cards with your mouse, tap any number.</p>
      </section>
    </main>
  );
}
