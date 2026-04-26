import { Shield } from 'lucide-react';
import Link from 'next/link';

export function Footer() {
  return (
    <footer className="border-t-6 border-foreground bg-secondary/10 mt-auto bk-noise">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="flex items-center gap-3">
            <div className="p-1 border-2 border-foreground bg-accent bk-shadow-sm">
              <Shield className="h-6 w-6 text-foreground" />
            </div>
            <span className="font-black uppercase tracking-tighter text-xl">Vigilens</span>
            <span className="hidden lg:inline text-foreground font-bold text-xs uppercase tracking-widest border-l-2 border-foreground pl-3">
              Disaster Misinformation Detection
            </span>
          </div>
          <div className="flex flex-wrap justify-center gap-6 text-xs font-black uppercase tracking-widest">
            <Link
              href="/how-it-works"
              className="hover:text-primary transition-all hover:translate-y-[-2px]"
            >
              How It Works
            </Link>
            <Link
              href="/incidents"
              className="hover:text-primary transition-all hover:translate-y-[-2px]"
            >
              Incidents
            </Link>
            <Link
              href="/bulletin"
              className="hover:text-primary transition-all hover:translate-y-[-2px]"
            >
              Bulletin
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-primary transition-all hover:translate-y-[-2px]"
            >
              GitHub
            </a>
          </div>
          <p className="text-[10px] font-black uppercase tracking-widest bg-foreground text-background px-3 py-1 bk-shadow-sm">
            © {new Date().getFullYear()} Vigilens. OPEN SOURCE FOR DISASTER RESPONSE.
          </p>
        </div>
      </div>
    </footer>
  );
}
