import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Gong Call Summarizer',
  description: 'Summarize your Gong calls with AI',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
} 