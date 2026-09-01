import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { MonitoringRefresh } from "@/components/workspace/monitoring-refresh";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return (
    <AppShell>
      {children}
      <MonitoringRefresh />
    </AppShell>
  );
}
