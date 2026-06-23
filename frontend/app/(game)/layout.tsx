"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import BrandThemeProvider from "@/components/layout/BrandThemeProvider";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import { useGameStore } from "@/lib/store/gameStore";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      gcTime: 5 * 60 * 1000,
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

function GameShell({ children }: { children: React.ReactNode }) {
  const session = useGameStore((s) => s.session);

  if (!session) {
    return <>{children}</>;
  }

  return (
    <BrandThemeProvider>
      <div className="flex h-screen bg-[#FAFBFC]">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-auto p-6 page-enter">{children}</main>
        </div>
      </div>
    </BrandThemeProvider>
  );
}

export default function GameLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <GameShell>{children}</GameShell>
    </QueryClientProvider>
  );
}
