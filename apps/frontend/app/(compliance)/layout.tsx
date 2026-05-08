import { ProjectProvider } from "@/lib/project-context";
import { ComplianceShell } from "./ComplianceShell";

export default function ComplianceLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <ComplianceShell>{children}</ComplianceShell>
    </ProjectProvider>
  );
}
