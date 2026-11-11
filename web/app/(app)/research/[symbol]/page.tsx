import type { Metadata } from "next";
import { DossierScreen } from "@/components/research/DossierScreen";

export async function generateMetadata(props: PageProps<"/research/[symbol]">): Promise<Metadata> {
  const { symbol } = await props.params;
  return { title: decodeURIComponent(symbol).toUpperCase() };
}

export default async function DossierPage(props: PageProps<"/research/[symbol]">) {
  const { symbol } = await props.params;
  return <DossierScreen symbol={decodeURIComponent(symbol).toUpperCase()} />;
}
