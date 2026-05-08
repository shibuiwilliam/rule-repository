import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import Providers from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rule Repository",
  description: "Manage, search, and enforce natural-language rules across your organization",
};

/**
 * Persona routing: the PersonaSwitcher component (components/PersonaSwitcher.tsx)
 * navigates users between department portals via client-side routing.
 *
 * Supported portals and their root paths:
 *   Engineering  -> /dashboard  (default, existing)
 *   HR           -> /hr
 *   Legal        -> /legal
 *   Compliance   -> /compliance
 *   Security     -> /security
 *   Finance      -> /finance
 *   Marketing    -> /marketing
 *   Admin        -> /admin
 *
 * Each portal uses a Next.js route group with its own layout and PersonaLayout
 * wrapper. See components/PersonaLayout.tsx for the shared shell.
 */

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <NextIntlClientProvider messages={messages}>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
