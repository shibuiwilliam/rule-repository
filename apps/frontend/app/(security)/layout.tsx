import { ProjectProvider } from "@/lib/project-context";
import { SecurityShell } from "./SecurityShell";

export default function SecurityLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <SecurityShell>{children}</SecurityShell>
    </ProjectProvider>
  );
}
