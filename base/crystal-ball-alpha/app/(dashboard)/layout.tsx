'use client';

import Link from 'next/link';
import { use, useState, Suspense } from 'react';
import { Button } from '@/components/ui/button';
import { Home, LogOut, Key } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { signOut } from '@/app/(login)/actions';
import { useRouter } from 'next/navigation';
import { User } from '@/lib/db/schema';
import useSWR, { mutate } from 'swr';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

function CrystalBallLogo({ className = 'h-7 w-7' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Outer glow */}
      <circle cx="16" cy="16" r="14" fill="url(#cbGlow)" opacity="0.3" />
      {/* Main orb */}
      <circle cx="16" cy="16" r="12" fill="url(#cbGrad)" stroke="url(#cbStroke)" strokeWidth="1.5" />
      {/* Inner highlight */}
      <ellipse cx="13" cy="12" rx="5" ry="4" fill="white" opacity="0.15" />
      {/* Coordinate cross */}
      <line x1="16" y1="6" x2="16" y2="26" stroke="rgba(255,255,255,0.15)" strokeWidth="0.5" />
      <line x1="6" y1="16" x2="26" y2="16" stroke="rgba(255,255,255,0.15)" strokeWidth="0.5" />
      {/* Center dot */}
      <circle cx="16" cy="16" r="1.5" fill="white" opacity="0.6" />
      <defs>
        <radialGradient id="cbGlow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#a855f7" />
          <stop offset="100%" stopColor="transparent" />
        </radialGradient>
        <linearGradient id="cbGrad" x1="4" y1="4" x2="28" y2="28">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="50%" stopColor="#6d28d9" />
          <stop offset="100%" stopColor="#4c1d95" />
        </linearGradient>
        <linearGradient id="cbStroke" x1="4" y1="4" x2="28" y2="28">
          <stop offset="0%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function UserMenu() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { data: user } = useSWR<User>('/api/user', fetcher);
  const router = useRouter();

  async function handleSignOut() {
    await signOut();
    mutate('/api/user');
    router.push('/');
  }

  if (!user) {
    return (
      <>
        <Link
          href="/pricing"
          className="text-sm font-medium text-gray-400 hover:text-white transition-colors"
        >
          Pricing
        </Link>
        <a
          href="https://github.com/sancovp/crystal-ball"
          target="_blank"
          className="text-sm font-medium text-gray-400 hover:text-white transition-colors"
        >
          Docs
        </a>
        <Button asChild className="rounded-full bg-violet-600 hover:bg-violet-500 text-white border-0">
          <Link href="/sign-up">Get Started</Link>
        </Button>
      </>
    );
  }

  return (
    <DropdownMenu open={isMenuOpen} onOpenChange={setIsMenuOpen}>
      <DropdownMenuTrigger>
        <Avatar className="cursor-pointer size-9 ring-2 ring-violet-500/50">
          <AvatarImage alt={user.name || ''} />
          <AvatarFallback className="bg-violet-900 text-violet-200">
            {user.email
              .split(' ')
              .map((n) => n[0])
              .join('')}
          </AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="flex flex-col gap-1 bg-gray-900 border-gray-800">
        <DropdownMenuItem className="cursor-pointer text-gray-300 focus:text-white focus:bg-gray-800">
          <Link href="/dashboard" className="flex w-full items-center">
            <Home className="mr-2 h-4 w-4" />
            <span>Dashboard</span>
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem className="cursor-pointer text-gray-300 focus:text-white focus:bg-gray-800">
          <Link href="/dashboard" className="flex w-full items-center">
            <Key className="mr-2 h-4 w-4" />
            <span>API Keys</span>
          </Link>
        </DropdownMenuItem>
        <form action={handleSignOut} className="w-full">
          <button type="submit" className="flex w-full">
            <DropdownMenuItem className="w-full flex-1 cursor-pointer text-gray-300 focus:text-white focus:bg-gray-800">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </button>
        </form>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Header() {
  return (
    <header className="border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
        <Link href="/" className="flex items-center gap-2.5 group">
          <CrystalBallLogo />
          <span className="text-xl font-bold bg-gradient-to-r from-violet-300 to-violet-500 bg-clip-text text-transparent">
            Crystal Ball
          </span>
        </Link>
        <div className="flex items-center space-x-4">
          <Suspense fallback={<div className="h-9" />}>
            <UserMenu />
          </Suspense>
        </div>
      </div>
    </header>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <section className="flex flex-col min-h-screen bg-gray-950">
      <Header />
      {children}
    </section>
  );
}
