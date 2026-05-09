"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PersonaSwitcher } from "./PersonaSwitcher";
import { LocaleSwitcher } from "./LocaleSwitcher";

export interface NavItem {
  label: string;
  href: string;
  icon: string;
}

interface PersonaLayoutProps {
  persona: string;
  personaIcon: string;
  accentColor: string;
  accentHover: string;
  navItems: NavItem[];
  children: React.ReactNode;
}

export function PersonaLayout({
  persona,
  personaIcon,
  accentColor,
  accentHover,
  navItems,
  children,
}: PersonaLayoutProps) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r bg-white">
        {/* Brand */}
        <div className="border-b px-4 py-4">
          <Link href="/" className="block text-lg font-bold tracking-tight text-gray-900">
            Rule Repository
          </Link>
        </div>

        {/* Persona switcher */}
        <div className="border-b px-4 py-3">
          <PersonaSwitcher />
        </div>

        {/* Portal header */}
        <div className="px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">{personaIcon}</span>
            <span className="text-sm font-semibold text-gray-700">{persona}</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-2">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== navItems[0]?.href && pathname.startsWith(item.href));
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? `${accentColor} ${accentHover}`
                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                    }`}
                  >
                    <span className="text-base">{item.icon}</span>
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t px-4 py-3">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Engineering
          </Link>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col">
        {/* Top bar */}
        <header className="flex h-14 items-center justify-between border-b bg-white px-6">
          <div className="text-sm text-gray-500">
            {persona} Portal
          </div>
          <div className="flex items-center gap-4">
            {/* Locale switcher */}
            <LocaleSwitcher />

            {/* Notifications bell */}
            <button
              type="button"
              className="relative rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              title="Notifications"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                />
              </svg>
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                3
              </span>
            </button>

            {/* User menu */}
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-sm font-medium text-gray-600">
                U
              </div>
              <span className="text-sm text-gray-700">User</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50 p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
