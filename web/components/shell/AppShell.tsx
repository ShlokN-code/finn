"use client";
// Phone-width column + bottom dock (Ask bar above the tab bar, thumb zone) + undo toast.
// On desktop every app route renders in a centred 430 px column; only "/" shows the QR landing.
import { Suspense, type ReactNode } from "react";
import { LazyMotion, domMax } from "framer-motion";
import { AskBar } from "./AskBar";
import { TabBar, TabBarStatic } from "./TabBar";
import { ToastHost } from "./Toast";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={domMax} strict>
      <div className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col bg-paper pb-[calc(112px+env(safe-area-inset-bottom))] min-[431px]:border-x min-[431px]:border-rule">
        {children}
      </div>
      <div className="fixed inset-x-0 bottom-0 z-30">
        <div className="mx-auto w-full max-w-[430px] bg-paper/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm min-[431px]:border-x min-[431px]:border-rule">
          <AskBar />
          <Suspense fallback={<TabBarStatic />}>
            <TabBar />
          </Suspense>
        </div>
      </div>
      <ToastHost />
    </LazyMotion>
  );
}
