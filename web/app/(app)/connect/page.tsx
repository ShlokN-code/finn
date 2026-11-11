import type { Metadata } from "next";
import { TelegramConnect } from "@/components/telegram/TelegramConnect";

export const metadata: Metadata = { title: "Telegram alerts" };

export default function ConnectPage() {
  return (
    <div className="px-4 pb-8 pt-6">
      <p className="t-micro text-ink-3">Push</p>
      <h1 className="t-display mt-1">Telegram alerts</h1>
      <div className="mt-4">
        <TelegramConnect />
      </div>
    </div>
  );
}
