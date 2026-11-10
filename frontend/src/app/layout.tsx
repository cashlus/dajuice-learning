import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Press_Start_2P, VT323 } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import { AuthGate } from "@/components/auth/auth-gate";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const pressStart = Press_Start_2P({
  variable: "--font-press-start",
  weight: "400",
  subsets: ["latin"],
});

const vt323 = VT323({
  variable: "--font-vt323",
  weight: "400",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DaJuice OS",
  applicationName: "DaJuice",
  description: "科目选择、概念卡片与专注练习组成的 Y2K 学习终端。",
  icons: {
    icon: [
      { url: "/icons/dajuice-32.png?v=y2k", sizes: "32x32", type: "image/png" },
      { url: "/icons/dajuice-48.png?v=y2k", sizes: "48x48", type: "image/png" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    apple: [
      { url: "/icons/dajuice-180.png?v=y2k", sizes: "180x180", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
  },
  appleWebApp: {
    capable: true,
    title: "DaJuice",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  themeColor: "#08060d",
  colorScheme: "dark",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="zh-CN"
      className={`dark ${geistSans.variable} ${geistMono.variable} ${pressStart.variable} ${vt323.variable} antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-dvh bg-background font-sans text-foreground">
        <AuthGate>{children}</AuthGate>
        <Toaster
          theme="dark"
          position="top-center"
          richColors
          closeButton
          duration={6_000}
        />
      </body>
    </html>
  );
}
