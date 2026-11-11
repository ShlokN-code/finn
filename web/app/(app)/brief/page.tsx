import type { Metadata } from "next";
import { BriefScreen } from "@/components/brief/BriefScreen";

export const metadata: Metadata = { title: "Brief" };

export default function BriefPage() {
  return <BriefScreen />;
}
