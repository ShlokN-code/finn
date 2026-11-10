// One card, opened directly (Telegram "Open in FINN"). Server-rendered from the API; never a blank error.
import type { Metadata } from "next";
import Link from "next/link";
import { CardView } from "@/components/cards";
import { apiFetch } from "@/lib/api";
import type { Card } from "@/lib/types";

export const metadata: Metadata = { title: "FINN · card" };

async function load(id: string): Promise<{ card?: Card; error?: string }> {
  try {
    const r = await apiFetch(`/events/${encodeURIComponent(id)}/card`);
    if (r.status === 404) return { error: "This event isn't in FINN any more (it may have been re-threaded)." };
    if (!r.ok) return { error: `The API answered ${r.status}.` };
    return { card: (await r.json()) as Card };
  } catch (e) {
    const timedOut = e instanceof Error && e.name === "TimeoutError";
    return { error: timedOut ? "The API is still waking up — refresh in a few seconds." : "The API is unreachable right now." };
  }
}

export default async function EventPage(props: PageProps<"/e/[id]">) {
  const { id: raw } = await props.params;
  let id = raw;
  try {
    id = decodeURIComponent(raw);
  } catch {
    // already decoded
  }
  const { card, error } = await load(id);
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-4 px-4 py-6">
      <header className="flex items-center justify-between">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          FINN
        </Link>
        <Link href="/connect" className="text-xs text-muted-foreground underline-offset-4 hover:underline">
          Telegram alerts
        </Link>
      </header>
      {card ? (
        <CardView card={card} />
      ) : (
        <div className="rounded-2xl border p-4 text-sm">
          <p className="font-medium">Couldn&apos;t load this card.</p>
          <p className="mt-1 text-muted-foreground">{error}</p>
        </div>
      )}
      <p className="text-[11px] text-muted-foreground">
        Every number is tappable: it opens its source document, page and quote. FINN reads primary sources only.
      </p>
    </main>
  );
}
