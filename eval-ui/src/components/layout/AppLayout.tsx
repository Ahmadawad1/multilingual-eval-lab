import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { getCurrentPage, Sidebar } from './Sidebar';
import { Header } from './Header';

export function AppLayout() {
  const [motion, setMotion] = useState(() => localStorage.getItem('eval-motion') !== 'paused');
  useEffect(() => {
    document.documentElement.dataset.motion = motion ? 'on' : 'paused';
  }, [motion]);
  const { pathname } = useLocation();
  const { group, item } = getCurrentPage(pathname);
  const title = group && item ? `${group.label} · ${item.label}` : '';

  return (
    <div className="work-shell relative flex h-dvh flex-col overflow-hidden md:flex-row">
      <Sidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <Header title={title} motion={motion} toggleMotion={() => {
          localStorage.setItem('eval-motion', motion ? 'paused' : 'on');
          setMotion(!motion);
        }} />
        <main className="flex-1 overflow-auto p-3 pb-16 md:p-6">
          <div key={pathname} className="work-page">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
