import type { Metadata } from "next";
import { ResearchHome } from "@/components/research/ResearchHome";

export const metadata: Metadata = { title: "Research" };

export default function ResearchPage() {
  return <ResearchHome />;
}
