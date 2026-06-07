import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PulseBoard – NHS A&E Performance",
  description: "Real-time NHS A&E attendance and 4-hour performance dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/90 px-6 py-3 backdrop-blur-sm">
          <a href="/" className="inline-flex items-center gap-2 hover:opacity-80">
            <span className="text-lg font-bold tracking-tight text-gray-900">
              PulseBoard
            </span>
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
              NHS A&amp;E
            </span>
          </a>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
