import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { AuroraBackground } from '@/components/ai/AuroraBackground';

const PAGE_TITLES: Record<string, string> = {
  '/evaluation/dataset':     'Evaluation · Golden Sets',
  '/evaluation/data-lab':    'Evaluation · Golden Sets',
  '/evaluation/retrieval':   'Evaluation · Retrieval',
  '/evaluation/normalization': 'Evaluation · Arabic Norm',
  '/evaluation/experiments': 'Evaluation · Experiments',
  '/evaluation/generation': 'Evaluation · Generation',
  '/evaluation/judges': 'Evaluation · Judge Lab',
  '/evaluation/gate': 'Evaluation · Release Gate',
  '/evaluation/stats':       'Evaluation · Stats Lab',
};

export function AppLayout() {
  const [motion, setMotion] = useState(() => localStorage.getItem('eval-motion') !== 'paused');
  useEffect(() => {
    document.documentElement.dataset.motion = motion ? 'on' : 'paused';
  }, [motion]);
  const { pathname } = useLocation();
  const title =
    PAGE_TITLES[pathname]
    ?? Object.entries(PAGE_TITLES).find(([path]) => path !== '/' && pathname.startsWith(`${path}/`))?.[1]
    ?? '';

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden md:flex-row">
      {motion && <AuroraBackground />}
      <Sidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <Header title={title} motion={motion} toggleMotion={() => {
          localStorage.setItem('eval-motion', motion ? 'paused' : 'on');
          setMotion(!motion);
        }} />
        <main className="flex-1 overflow-auto p-3 pb-16 md:p-6">
          <div key={pathname} className="animate-fade-in-up">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}