'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { Shield, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ModeToggle } from './ModeToggle';
import { cn } from '@/lib/utils';
import { useState } from 'react';

export function Navbar() {
  const { t, i18n } = useTranslation();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLinks = [
    { href: '/', label: t('nav.home') },
    { href: '/analysis', label: t('nav.analysis') },
    { href: '/incidents', label: t('nav.incidents') },
    { href: '/bulletin', label: t('nav.bulletin') },
    { href: '/how-it-works', label: t('nav.howItWorks') },
  ];

  const languages = ['en', 'hi', 'ta', 'ar', 'es'];

  return (
    <nav className="sticky top-0 z-50 border-b-4 border-foreground bg-background bk-noise">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-20 items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="p-1 border-3 border-foreground bg-primary bk-shadow-sm group-hover:translate-x-[2px] group-hover:translate-y-[2px] group-hover:shadow-none transition-all">
              <Shield className="h-8 w-8 text-primary-foreground" />
            </div>
            <span className="text-2xl font-black uppercase tracking-tighter">Vigilens</span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'text-sm font-black uppercase tracking-widest transition-all hover:translate-y-[-2px] hover:text-primary',
                  pathname === link.href ? 'text-primary underline decoration-4 underline-offset-8' : 'text-foreground'
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <select
              value={i18n.language}
              onChange={(e) => i18n.changeLanguage(e.target.value)}
              className="text-xs font-black bg-background border-3 border-foreground px-3 py-1 bk-shadow-sm focus:outline-none"
            >
              {languages.map((lang) => (
                <option key={lang} value={lang}>
                  {lang.toUpperCase()}
                </option>
              ))}
            </select>
            <ModeToggle />
            <Button
              variant="outline"
              size="icon"
              className="md:hidden border-3"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              <Menu className="h-6 w-6" />
            </Button>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden border-t-4 border-foreground py-6 space-y-2 bg-background">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'block px-4 py-3 text-lg font-black uppercase border-3 border-transparent',
                  pathname === link.href
                    ? 'bg-primary text-primary-foreground border-foreground bk-shadow-sm'
                    : 'text-foreground hover:bg-secondary/20'
                )}
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
