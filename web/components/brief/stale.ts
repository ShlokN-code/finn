// Is the filings feed behind? Checks run every 30 min, 08:30–22:00 IST on weekdays (DECISIONS: filing checks).
// Stale = the last successful check is more than 2 h older than the most recent slot that should have run.
export function lastExpectedCheck(now = new Date()): Date {
  const ist = new Date(now.getTime() + 5.5 * 3600 * 1000); // shift so UTC getters read IST
  for (let back = 0; back < 8; back++) {
    const d = new Date(Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate() - back));
    const dow = d.getUTCDay();
    if (dow === 0 || dow === 6) continue;
    const open = d.getTime() + 8.5 * 3600 * 1000;
    const close = d.getTime() + 22 * 3600 * 1000;
    const t = back === 0 ? Math.min(ist.getTime(), close) : close;
    if (t < open) continue;
    return new Date(t - 5.5 * 3600 * 1000);
  }
  return now;
}

export function isStale(dataAsOf: string | null, now = new Date()): boolean {
  if (!dataAsOf) return true;
  return lastExpectedCheck(now).getTime() - Date.parse(dataAsOf) > 2 * 3600 * 1000;
}
