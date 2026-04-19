import type { ReactNode } from 'react';
import { AreaChart, CloudSnow, CheckSquare, Settings, Hexagon } from 'lucide-react';

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#050506] text-[#EDEDEF] selection:bg-[#5E6AD2]/30 font-sans">
      
      {/* Background Ambient Layer */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,#0a0a0f_0%,#050506_50%,#020203_100%)] opacity-100"></div>
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 bg-[length:64px_64px] bg-[linear-gradient(to_right,#ffffff_1px,transparent_1px),linear-gradient(to_bottom,#ffffff_1px,transparent_1px)] opacity-[0.02]"></div>
      </div>

      {/* 1. Global Navigation (Left Sidebar) */}
      <aside className="relative z-50 flex w-16 flex-col items-center border-r border-white/[0.06] bg-[#020203] py-6">
        <div className="mb-8" title="App Logo">
          <Hexagon size={28} strokeWidth={1.5} className="text-[#EDEDEF] opacity-90" />
        </div>
        <nav className="flex flex-1 flex-col gap-4">
          <a href="/stocks" className="group flex h-11 w-11 items-center justify-center rounded-xl bg-[#5E6AD2]/20 text-[#5E6AD2] shadow-[inset_2px_0_0_#5E6AD2] transition-all duration-300 ease-out hover:-translate-y-1 hover:bg-[#5E6AD2]/30 active:scale-95" title="Stock Analysis">
            <AreaChart size={22} strokeWidth={2} />
          </a>
          <a href="/weather" className="flex h-11 w-11 items-center justify-center rounded-xl text-[#8A8F98] transition-all duration-300 ease-out hover:-translate-y-1 hover:bg-white/[0.05] hover:text-[#EDEDEF] active:scale-95" title="Weather">
            <CloudSnow size={22} strokeWidth={2} />
          </a>
          <a href="/tasks" className="flex h-11 w-11 items-center justify-center rounded-xl text-[#8A8F98] transition-all duration-300 ease-out hover:-translate-y-1 hover:bg-white/[0.05] hover:text-[#EDEDEF] active:scale-95" title="Tasks">
            <CheckSquare size={22} strokeWidth={2} />
          </a>
        </nav>
        <div className="mt-auto">
          <a href="/settings" className="flex h-11 w-11 items-center justify-center rounded-xl text-[#8A8F98] transition-all duration-300 ease-out hover:-translate-y-1 hover:bg-white/[0.05] hover:text-[#EDEDEF] active:scale-95" title="Settings">
            <Settings size={22} strokeWidth={2} />
          </a>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="relative z-10 flex flex-1 flex-col">
        {/* 2. Local Navigation (Top Bar) */}
        <header className="sticky top-0 z-40 flex h-16 items-center border-b border-white/[0.06] bg-[#0a0a0c]/70 px-8 backdrop-blur-xl">
          <h1 className="mr-12 text-sm font-medium tracking-tight text-[#EDEDEF]">Stock Analysis</h1>
          <nav className="flex h-full gap-8">
            <a href="/stocks/history" className="relative flex items-center text-sm font-medium text-[#EDEDEF]">
              History
              <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t-sm bg-[#5E6AD2]"></span>
            </a>
          </nav>
        </header>

        {/* 3. Render the active page here */}
        <main className="flex-1 overflow-y-auto p-8 text-[#8A8F98] bg-transparent">
          {children}
        </main>
      </div>
    </div>
  );
}
