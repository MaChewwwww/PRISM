import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PRISM — One signal. Multiple perspectives. Better decisions.",
  description: "One signal. Multiple perspectives. Better decisions.",
  openGraph: {
    title: "PRISM — One signal. Multiple perspectives. Better decisions.",
    description: "One signal. Multiple perspectives. Better decisions.",
    siteName: "PRISM",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "PRISM — One signal. Multiple perspectives. Better decisions.",
    description: "One signal. Multiple perspectives. Better decisions.",
  },
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
