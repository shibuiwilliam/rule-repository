import { ProjectProvider } from "@/lib/project-context";
import { HrShell } from "./HrShell";

export default function HrLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <HrShell>{children}</HrShell>
    </ProjectProvider>
  );
}
