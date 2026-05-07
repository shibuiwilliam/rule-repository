import { ProjectProvider } from "@/lib/project-context";
import { PersonaProvider } from "./PersonaSwitcher";
import { Sidebar } from "./Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <PersonaProvider>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 bg-gray-50 p-8">{children}</main>
        </div>
      </PersonaProvider>
    </ProjectProvider>
  );
}
