import { ProjectProvider } from "@/lib/project-context";
import { SalesShell } from "./SalesShell";

export default function SalesLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <SalesShell>{children}</SalesShell>
    </ProjectProvider>
  );
}
