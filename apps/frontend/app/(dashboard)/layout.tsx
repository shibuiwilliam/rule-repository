import Link from "next/link";

const NAV_ITEMS = [
  { href: "/rules", label: "Rules", section: "manage" },
  { href: "/search", label: "Search", section: "manage" },
  { href: "/documents", label: "Documents", section: "manage" },
  { href: "/discover", label: "Discover", section: "manage" },
  { href: "/federations", label: "Federations", section: "manage" },
  { href: "/playground", label: "Playground", section: "manage" },
  { href: "/snapshots", label: "Snapshots", section: "manage" },
  { href: "/intelligence", label: "Intelligence", section: "observe" },
  { href: "/feedback", label: "Feedback", section: "observe" },
  { href: "/gateway", label: "Gateway", section: "enforce" },
  { href: "/integrations", label: "Integrations", section: "enforce" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-white px-4 py-6">
        <Link href="/" className="mb-8 block text-xl font-bold tracking-tight">
          Rule Repository
        </Link>

        <nav className="space-y-6">
          <div>
            <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Manage
            </p>
            {NAV_ITEMS.filter((i) => i.section === "manage").map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                {item.label}
              </Link>
            ))}
          </div>

          <div>
            <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Observe
            </p>
            {NAV_ITEMS.filter((i) => i.section === "observe").map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                {item.label}
              </Link>
            ))}
          </div>

          <div>
            <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Enforce
            </p>
            {NAV_ITEMS.filter((i) => i.section === "enforce").map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-gray-50 p-8">{children}</main>
    </div>
  );
}
