import type { Metadata } from "next";
import localFont from "next/font/local";
import { Toaster } from "sonner";
import "./globals.css";
import { AuthProvider } from "@/contexts/auth-context";
import { ThemeProvider } from "@/contexts/theme-context";
import { ConnectivityBanner } from "@/components/connectivity-banner";
import { ErrorBoundary } from "@/components/error-boundary";

const appSans = localFont({
  src: "../fonts/GoogleSansFlex-VariableFont.ttf",
  variable: "--font-sans",
  display: "swap",
});
const googleSansFlex = localFont({
  src: "../fonts/GoogleSansFlex-VariableFont.ttf",
  variable: "--font-heading",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Klarnow AI",
  description: "Campaign packs, strategy, and Klaro — your AI co-pilot",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, viewport-fit=cover"
        />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <meta name="theme-color" content="#FFFFFF" />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('klarnow-theme');var r=t==='light'?'light':t==='system'?(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):'light';document.documentElement.classList.add(r);var c=r==='dark'?'#000000':'#FFFFFF';var m=document.querySelector('meta[name="theme-color"]');if(!m){m=document.createElement('meta');m.setAttribute('name','theme-color');document.head.appendChild(m);}m.setAttribute('content',c);})();`,
          }}
        />
      </head>
      <body
        className={`${appSans.variable} ${googleSansFlex.variable} font-sans min-h-screen antialiased`}
      >
        <ThemeProvider>
          <ConnectivityBanner />
          <ErrorBoundary>
            <AuthProvider>{children}</AuthProvider>
          </ErrorBoundary>
        </ThemeProvider>
        <Toaster position="bottom-right" richColors closeButton />
      </body>
    </html>
  );
}
