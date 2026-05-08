import Link from "next/link";
import { ProjectProvider } from "@/lib/project-context";

export default function FinanceLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <div className="flex min-h-screen">
        <nav className="w-64 bg-emerald-800 text-white p-6">
          <h2 className="text-lg font-semibold mb-6">Finance</h2>
          <ul className="space-y-2">
            <li>
              <Link href="/transactions" className="block px-3 py-2 rounded hover:bg-emerald-700">
                Transactions
              </Link>
            </li>
            <li>
              <Link href="/rules?scope=finance" className="block px-3 py-2 rounded hover:bg-emerald-700">
                Finance Rules
              </Link>
            </li>
            <li>
              <Link href="/audit" className="block px-3 py-2 rounded hover:bg-emerald-700">
                Audit
              </Link>
            </li>
          </ul>
        </nav>
        <main className="flex-1 bg-gray-50 p-8">{children}</main>
      </div>
    </ProjectProvider>
  );
}
