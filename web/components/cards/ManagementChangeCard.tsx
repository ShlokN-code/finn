// Management change: the incoming person's mini-CV — filing first, web snippets marked as such.
import type { ManagementDetail } from "@/lib/types";
import { FigureValue } from "./FigureValue";

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
                    {r.start_year ? ` (${r.start_year}${r.end_year && r.end_year !== r.start_year ? `–${r.end_year}` : r.end_year ? "" : "–"})` : ""}
                  </a>
                  {r.source === "web" && <span className="text-muted-foreground"> · web</span>}
                </li>
              ))}
            </ul>
          )}
          {p.qualifications.length > 0 && (
            <p className="mt-1 text-xs text-muted-foreground">{p.qualifications.map((q) => q.text).join(" · ")}</p>
          )}
        </section>
      ))}
      <p className="text-[11px] text-muted-foreground">
        {d.web_enrichment === "done"
          ? "Items marked “web” come from search snippets and are unverified."
          : d.web_enrichment === "unavailable"
            ? "From the filing only (web background not available right now)."
            : "From the filing."}
      </p>
    </div>
  );
}
