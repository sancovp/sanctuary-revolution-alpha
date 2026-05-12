import './globals.css';
import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { getUser, getTeamForUser } from '@/lib/db/queries';
import { SWRConfig } from 'swr';

export const metadata: Metadata = {
  title: 'Crystal Ball — Ontological Navigation for AI Agents',
  description:
    'Crystal Ball is a coordinate-based ontology engine that gives AI agents structured memory, spatial reasoning, and composable knowledge graphs via MCP.',
  keywords: [
    'Crystal Ball',
    'MCP',
    'AI agents',
    'ontology',
    'knowledge graph',
    'coordinate system',
  ],
};

export const viewport: Viewport = {
  maximumScale: 1,
};

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`bg-gray-950 text-white ${inter.className}`}
    >
      <body className="min-h-[100dvh] bg-gray-950">
        <SWRConfig
          value={{
            fallback: {
              '/api/user': getUser(),
              '/api/team': getTeamForUser(),
            },
          }}
        >
          {children}
        </SWRConfig>
      </body>
    </html>
  );
}
