import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LingoSphere Admin — Control Console",
  description: "Operations, latency tracking, prompt firewalls, and AI safety console.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <style>{`
          body {
            font-family: 'Outfit', sans-serif;
          }
        `}</style>
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
