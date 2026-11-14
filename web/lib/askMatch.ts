// Which company a free-text question names, for Ask on Brief and Portfolio. Plain string matching against the NSE
// list (no model): a company's name ("Infosys", "HDFC Bank"), or its NSE symbol typed in capitals ("INFY"). For the
// user's holdings and the companies FINN has research on, the symbol in any case ("infy") and a distinctive first
// word ("Reliance", "Persistent") also count. At most one company is returned: the longest name wins.

export type Named = { symbol: string; name: string };
export type NameIndex = { phrases: [string, string][]; names: Map<string, string> };

// Acronyms that appear in questions about results, never meant as a ticker.
const NOT_TICKERS = new Set(
  "NSE BSE CEO CFO COO MD EPS PAT NII PPOP GST RBI SEBI IT AI US USA UK EU GDP IPO QIP OFS ESG AGM EGM EBIT EBITDA ROE ROA ROCE NIM NPA GNPA NNPA CASA AUM MSME ARPU PLI EV CAGR YOY QOQ TTM FY H1 H2 Q1 Q2 Q3 Q4 FII DII PE PB OK".split(" "),
);
// Single words that are also some company's whole name but usually mean the ordinary word in a question.
const ORDINARY = new Set(
  "growth margin margins guidance results result debt capital finance power energy steel bank global india indian international order orders book future prime focus vision quality value standard general united first star super smart sterling gold silver advance delta alpha omega apex pace plus premier supreme ideal idea cupid amal atul".split(
    " ",
  ),
);

const norm = (s: string) =>
  ` ${s
    .toLowerCase()
    .replace(/&/g, " & ")
    .replace(/[^a-z0-9&]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()} `;

/** "Polycab India Limited" → ["polycab india", "polycab"]; "Bank of India Limited" keeps "bank of india". */
function phrasesFor(name: string): string[] {
  const base = norm(name.replace(/\(india\)/i, " ").replace(/\s+(limited|ltd\.?)\s*$/i, "")).trim();
  const out = [base];
  const words = base.split(" ");
  if (words.length > 1 && words.at(-1) === "india" && words.at(-2) !== "of") out.push(words.slice(0, -1).join(" "));
  return out.filter((p) => p.length >= 4 && !(p.split(" ").length === 1 && ORDINARY.has(p)));
}

export function buildIndex(list: [string, string][]): NameIndex {
  const phrases: [string, string][] = [];
  for (const [s, n] of list) for (const p of phrasesFor(n)) phrases.push([s, p]);
  return { phrases, names: new Map(list) };
}

/** `mine` = the user's holdings plus the companies with research: they also match by first word and any-case symbol. */
export function findCompany(question: string, index: NameIndex, mine: Iterable<string>): Named | null {
  const q = norm(question);
  if (q.trim().length < 2) return null;
  const mineSet = new Set(mine);
  let best: { symbol: string; len: number } | null = null;
  const consider = (symbol: string, phrase: string) => {
    if (!q.includes(` ${phrase} `)) return;
    const better = !best || phrase.length > best.len || (phrase.length === best.len && mineSet.has(symbol) && !mineSet.has(best.symbol));
    if (better) best = { symbol, len: phrase.length };
  };
  for (const [s, p] of index.phrases) consider(s, p);
  // A distinctive first word, only where it points to one of the user's companies ("Tata" stays ambiguous).
  const first = new Map<string, string[]>();
  for (const s of mineSet) {
    const n = index.names.get(s);
    const w = n ? norm(n).trim().split(" ")[0] : "";
    if (w.length >= 4 && !ORDINARY.has(w)) first.set(w, [...(first.get(w) ?? []), s]);
  }
  for (const [w, syms] of first) if (syms.length === 1) consider(syms[0], w);
  const found = best as { symbol: string; len: number } | null;
  if (found) return { symbol: found.symbol, name: index.names.get(found.symbol) ?? found.symbol };

  for (const t of question.match(/[A-Za-z0-9&-]+/g) ?? []) {
    const T = t.toUpperCase();
    if (!index.names.has(T) || NOT_TICKERS.has(T)) continue;
    const typedAsSymbol = t === T && /[A-Z]/.test(T) && T.length >= 2;
    const oneOfMine = mineSet.has(T) && T.length >= 3 && !ORDINARY.has(t.toLowerCase());
    if (typedAsSymbol || oneOfMine) return { symbol: T, name: index.names.get(T)! };
  }
  return null;
}
