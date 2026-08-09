import { Construction, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { Alert, StatePanel } from "../components/feedback";
import { Drawer } from "../components/overlays";
import { Button } from "../components/primitives";
import type { PortalRoute } from "../app/routes";

export function FeatureShellPage({
  route,
}: {
  route: PortalRoute;
}): React.ReactNode {
  const [filtersOpen, setFiltersOpen] = useState(false);
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>{route.label}</h1>
          <p>{route.description}</p>
        </div>
        <Button
          variant="secondary"
          icon={<SlidersHorizontal size={18} />}
          onClick={() => setFiltersOpen(true)}
        >
          View filter shell
        </Button>
      </header>
      <Alert tone="info" title={`Scheduled for ${route.phase}`}>
        This route is present for stable navigation and permission testing. Its
        operational workflow is intentionally inactive.
      </Alert>
      <section className="inactive-workspace">
        <StatePanel
          title={`${route.label} is not active yet`}
          description="No operational records, counts or success state are being simulated in P05."
        />
      </section>
      <Drawer
        open={filtersOpen}
        title={`${route.label} filters`}
        onClose={() => setFiltersOpen(false)}
      >
        <Alert tone="neutral">
          Filter controls will be connected to server-side pagination in{" "}
          {route.phase}. No placeholder query is sent now.
        </Alert>
        <div className="drawer-placeholder" aria-hidden="true">
          <Construction size={36} />
        </div>
      </Drawer>
    </div>
  );
}
