import { ProjectProvider } from "@/lib/project-context";
import { MarketingShell } from "./MarketingShell";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <MarketingShell>{children}</MarketingShell>
    </ProjectProvider>
  );
}
