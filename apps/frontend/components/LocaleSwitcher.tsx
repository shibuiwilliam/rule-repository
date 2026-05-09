"use client";

import { useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

const SUPPORTED_LOCALES = [
  { code: "en", label: "EN" },
  { code: "ja", label: "JA" },
] as const;

export function LocaleSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function handleChange(newLocale: string) {
    // Set locale cookie and reload
    document.cookie = `NEXT_LOCALE=${newLocale};path=/;max-age=31536000`;
    startTransition(() => {
      router.refresh();
    });
  }

  return (
    <div className="flex items-center gap-1">
      {SUPPORTED_LOCALES.map((loc) => (
        <button
          key={loc.code}
          type="button"
          onClick={() => handleChange(loc.code)}
          disabled={isPending}
          className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
            locale === loc.code
              ? "bg-gray-200 text-gray-800"
              : "text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          } ${isPending ? "opacity-50" : ""}`}
          title={`Switch to ${loc.label}`}
        >
          {loc.label}
        </button>
      ))}
    </div>
  );
}
