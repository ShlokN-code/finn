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
    <div className="pb-8">
      <div className="flex h-12 items-center px-2">
        <Link href="/brief" className="inline-flex h-11 items-center rounded-full px-2 text-[15px] text-ink-2">
          ‹ Brief
        </Link>
      </div>
      {card ? (
        <div className="border-y border-rule">
          <CardView card={card} />
        </div>
      ) : (
        <div className="px-4 py-8">
          <p className="t-headline">Couldn&apos;t load this card.</p>
          <p className="t-small mt-1 text-ink-2">{error}</p>
        </div>
      )}
      <p className="t-small px-4 pt-4 text-ink-3">
        Every number is tappable: it opens its source document, page and quote. FINN reads primary sources only.
      </p>
    </div>
  );
}
