import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "My Photos — Personal Gallery",
  description: "A personal photo gallery for storing and organizing your memories.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
