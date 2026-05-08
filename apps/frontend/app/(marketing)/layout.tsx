import Link from "next/link";
import { ProjectProvider } from "@/lib/project-context";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <div className="flex min-h-screen">
        <nav className="w-64 bg-purple-800 text-white p-6">
          <h2 className="text-lg font-semibold mb-6">Marketing</h2>
          <ul className="space-y-2">
            <li>
              <Link href="/creatives/review" className="block px-3 py-2 rounded hover:bg-purple-700">
                Creative Review
              </Link>
            </li>
            <li>
              <Link href="/rules?scope=marketing" className="block px-3 py-2 rounded hover:bg-purple-700">
                Marketing Rules
              </Link>
            </li>
          </ul>
        </nav>
        <main className="flex-1 bg-gray-50 p-8">{children}</main>
      </div>
    </ProjectProvider>
  );
}
