export default function Loading() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-4 px-4 py-6">
      <p className="text-lg font-semibold tracking-tight">FINN</p>
      <div className="animate-pulse rounded-2xl border p-4">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="mt-3 h-4 w-3/4 rounded bg-muted" />
        <div className="mt-2 h-3 w-1/2 rounded bg-muted" />
        <div className="mt-4 h-20 rounded bg-muted" />
      </div>
      <p className="text-xs text-muted-foreground">Loading… (the free-tier API can take up to ~50 s to wake)</p>
    </main>
  );
}
