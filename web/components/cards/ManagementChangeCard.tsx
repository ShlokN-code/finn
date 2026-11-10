// Management change: the incoming person's mini-CV — filing first. Every web fact says "web · unverified",
// names its kind of source (profile, bio page, prior employer, news) and links to the snippet's URL.
import type { Citation, ManagementDetail } from "@/lib/types";
import { FigureValue } from "./FigureValue";

function WebTag({ c }: { c: Citation }) {
  const kind = c.title?.split(" · ")[0];
  return (
    <a
      href={c.url}
      target="_blank"
      rel="noopener noreferrer"
      title={c.quote ? `“${c.quote}”` : undefined}
      className="ml-1 whitespace-nowrap text-[11px] text-amber-700 underline-offset-2 hover:underline dark:text-amber-300"
    >
      web · unverified{kind ? ` · ${kind}` : ""} ↗
    </a>
  );
}

function years(start?: number | null, end?: number | null) {
  if (!start) return "";
  return ` (${start}${end && end !== start ? `–${end}` : end ? "" : "–"})`;
}

export function ManagementBody({ d }: { d: ManagementDetail }) {
  if (d.people.length === 0) return <p className="text-xs text-muted-foreground">No profile found in the filing.</p>;
  return (
    <div className="space-y-4">
      {d.people.map((p) => (
        <section key={p.name} className="text-sm">
          <p className="font-medium">
            {p.name} <span className="font-normal text-muted-foreground">— {p.role}, {p.change.replace("_", "-")}</span>
          </p>
          {p.insider !== null && (
            <p className="text-xs">
              {p.insider ? "Insider" : "Outside hire"}
              {p.insider_reason && <span className="text-muted-foreground"> · {p.insider_reason}</span>}
            </p>
          )}
          {p.tenure_years && (
            <p className="text-xs">
              Tenure at the company: <FigureValue f={p.tenure_years} />
            </p>
          )}
          {p.prior_roles.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-xs">
              {p.prior_roles.map((r, i) => (
                <li key={i}>
                  <a href={r.citation.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    {r.role ? `${r.role}, ` : ""}
                    {r.company}
                    {r.period_citation ? "" : years(r.start_year, r.end_year)}
                  </a>
                  {r.period_citation && (
                    <>
                      {years(r.start_year, r.end_year)}
                      <WebTag c={r.period_citation} />
                    </>
                  )}
                  {r.source === "web" && <WebTag c={r.citation} />}
                </li>
              ))}
            </ul>
          )}
          {p.qualifications.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
              {p.qualifications.map((q, i) => (
                <li key={i}>
                  {q.text}
                  {q.status !== "verified" && q.citations[0] && <WebTag c={q.citations[0]} />}
                </li>
              ))}
            </ul>
          )}
          {p.achievements.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-xs">
              {p.achievements.map((a, i) => (
                <li key={i}>
                  {a.text}
                  {a.citations[0] && <WebTag c={a.citations[0]} />}
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
      <p className="text-[11px] text-muted-foreground">
        {d.web_enrichment === "done"
          ? "Items marked “web · unverified” come from search snippets, not the filing."
          : d.web_enrichment === "unavailable"
            ? "From the filing only (web background not available right now)."
            : d.web_enrichment === "nothing_found"
              ? "From the filing. Web search found nothing it doesn't already say."
              : "From the filing."}
      </p>
    </div>
  );
}
