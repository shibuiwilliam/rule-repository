import { ProjectProvider } from "@/lib/project-context";
import { AdminShell } from "./AdminShell";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <AdminShell>{children}</AdminShell>
    </ProjectProvider>
  );
}
