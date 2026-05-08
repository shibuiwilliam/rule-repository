import { ProjectProvider } from "@/lib/project-context";
import { FinanceShell } from "./FinanceShell";

export default function FinanceLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <FinanceShell>{children}</FinanceShell>
    </ProjectProvider>
  );
}
