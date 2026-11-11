import { Skeleton } from "@/components/shell/StateView";

export default function Loading() {
  return (
    <div className="pt-12">
      <Skeleton rows={1} label="Loading card" />
      <p className="t-small px-4 pt-3 text-ink-3">Loading… the free-tier server can take up to a minute to wake.</p>
    </div>
  );
}
