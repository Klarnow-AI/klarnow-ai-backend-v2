import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";
import { Toaster } from "sonner";
import "./globals.css";
import { AuthProvider } from "@/contexts/auth-context";
import { ThemeProvider } from "@/contexts/theme-context";
import { ErrorBoundary } from "@/components/error-boundary";
import { PWAProvider } from "@/components/pwa-provider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-geist-sans",
});
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});
const googleSansFlex = localFont({
  src: "../fonts/GoogleSansFlex-VariableFont.ttf",
  variable: "--font-heading",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Klarnow AI",
  description: "Campaign packs, strategy, and Klaro — your AI co-pilot",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  manifest: "/site.webmanifest",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('klarnow-theme');var r=t==='light'?'light':t==='system'?(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):'light';document.documentElement.classList.add(r);})();`,
          }}
        />
      </head>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} ${googleSansFlex.variable} font-sans min-h-screen antialiased`}
      >
        <ThemeProvider>
          <PWAProvider>
            <ErrorBoundary>
              <AuthProvider>{children}</AuthProvider>
            </ErrorBoundary>
          </PWAProvider>
        </ThemeProvider>
        <Toaster position="bottom-right" richColors closeButton />
      </body>
    </html>
  );
}
