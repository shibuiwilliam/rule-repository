import { ProjectProvider } from "@/lib/project-context";
import { LegalShell } from "./LegalShell";

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <LegalShell>{children}</LegalShell>
    </ProjectProvider>
  );
}
