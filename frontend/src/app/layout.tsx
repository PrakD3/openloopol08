import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Footer } from '@/components/layout/Footer';
import { Navbar } from '@/components/layout/Navbar';
import { ModeProvider } from '@/context/ModeContext';
import { I18nProvider } from '@/i18n/provider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Vigilens — Disaster Video Misinformation Detection',
  description:
    'AI-powered platform to detect misinformation in disaster videos using deepfake detection, source hunting, and context analysis.',
  keywords: ['misinformation', 'disaster', 'AI', 'deepfake', 'fact-check'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <I18nProvider>
          <ModeProvider>
            <div className="min-h-screen flex flex-col">
              <Navbar />
              <main className="flex-1">{children}</main>
              <Footer />
            </div>
          </ModeProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
