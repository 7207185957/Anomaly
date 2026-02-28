import type { Metadata } from "next";
import "./globals.css";
import { AppProviders } from "@/providers/AppProviders";

export const metadata: Metadata = {
  title: "Enterprise AIOps Control Plane",
  description: "Enterprise incident, health, logs and topology console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
