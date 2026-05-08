import Link from "next/link";
import { ProjectProvider } from "@/lib/project-context";

export default function HrLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <div className="flex min-h-screen">
        <nav className="w-64 bg-indigo-800 text-white p-6">
          <h2 className="text-lg font-semibold mb-6">HR</h2>
          <ul className="space-y-2">
            <li>
              <Link href="/events" className="block px-3 py-2 rounded hover:bg-indigo-700">
                Event Review
              </Link>
            </li>
            <li>
              <Link href="/rules?scope=hr" className="block px-3 py-2 rounded hover:bg-indigo-700">
                HR Rules
              </Link>
            </li>
            <li>
              <Link href="/proposals?department=hr" className="block px-3 py-2 rounded hover:bg-indigo-700">
                Proposals
              </Link>
            </li>
          </ul>
        </nav>
        <main className="flex-1 bg-gray-50 p-8">{children}</main>
      </div>
    </ProjectProvider>
  );
}
