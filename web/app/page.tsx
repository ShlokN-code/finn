// "/" — desktop widths get the QR landing with a live phone preview; phones go straight into the Brief.
// The switch is CSS-only (no flash); on desktop the hidden Brief never fetches (gateDesktop).
import { BriefScreen } from "@/components/brief/BriefScreen";
import { Landing } from "@/components/landing/Landing";
import { AppShell } from "@/components/shell/AppShell";

export default function Home() {
  return (
    <>
      <div className="hidden lg:block">
        <Landing />
      </div>
      <div className="lg:hidden">
        <AppShell>
          <BriefScreen gateDesktop />
        </AppShell>
      </div>
    </>
  );
}
