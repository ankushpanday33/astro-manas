import type { Metadata } from "next";
import Link from "next/link";
import { NumberToggle, SettingsProvider } from "@/lib/settings";
import "./globals.css";

export const metadata: Metadata = {
  title: "Astro Manas",
  description: "An astro brain for every user: a stored chart, cited facts, rehearsed decisions, a visible decision network.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SettingsProvider>
          <header className="topbar">
            <Link href="/" className="brand">
              <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true"><circle cx="13" cy="13" r="12" fill="#FF6623" /><circle cx="13" cy="13" r="5" fill="#fff" /></svg>
              Astro Manas <span className="tag">an astro brain for every user</span>
            </Link>
            <nav>
              <Link href="/">Dashboard</Link>
              <Link href="/#customers">Users</Link>
              <Link href="/data">Upload data</Link>
              <Link href="/apps">Apps tracked</Link>
              <Link href="/integrations">Integrations</Link>
              <Link href="/how">How it decides</Link>
            </nav>
            <div className="right">
              <NumberToggle />
            </div>
          </header>
          {children}
          <footer className="footer">
            <span>Astro Manas · open source</span>
            <span>Every decision, with its receipts.</span>
          </footer>
        </SettingsProvider>
      </body>
    </html>
  );
}
