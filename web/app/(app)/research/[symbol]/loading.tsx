import { Skeleton } from "@/components/shell/StateView";

export default function Loading() {
  return (
    <div className="pt-14">
      <div className="mx-4 mb-4 h-6 w-40 animate-pulse rounded bg-surface-2" />
      <Skeleton rows={4} label="Loading dossier" />
    </div>
  );
}
