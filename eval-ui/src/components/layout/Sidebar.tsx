import type { ElementType } from 'react';
import { Link, matchPath, useLocation } from 'react-router-dom';
import {
  Database, FlaskConical, Gavel, GitPullRequestArrow,
  Languages, MessageSquareQuote, Scale, Search, Sigma,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  icon: ElementType;
  label: string;
  tabs?: string[];
}

interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

const GROUPS: NavGroup[] = [
  {
    id: 'data',
    label: 'Evaluation Data',
    items: [
      { to: '/evaluation/dataset', icon: Database, label: 'Golden Sets' },
      { to: '/evaluation/normalization', icon: Languages, label: 'Arabic Normalization' },
    ],
  },
  {
    id: 'playground',
    label: 'Playground',
    items: [
      { to: '/evaluation/retrieval', icon: Search, label: 'Retrieval Probe' },
      { to: '/evaluation/generation', icon: FlaskConical, label: 'RAGAS Metrics' },
      { to: '/evaluation/stats', icon: Sigma, label: 'Statistics Lab' },
    ],
  },
  {
    id: 'experiments',
    label: 'Evaluation Runs',
    items: [
      { to: '/evaluation/retrieval?tab=score', icon: Search, label: 'Retrieval Evaluation', tabs: ['score', 'compare'] },
      { to: '/evaluation/generation?tab=pipeline', icon: MessageSquareQuote, label: 'Generation Evaluation', tabs: ['pipeline', 'components', 'compare'] },
      { to: '/evaluation/experiments', icon: Scale, label: 'Retrieval Experiments' },
    ],
  },
  {
    id: 'quality',
    label: 'Quality & Release',
    items: [
      { to: '/evaluation/judges', icon: Gavel, label: 'Judge Calibration' },
      { to: '/evaluation/gate', icon: GitPullRequestArrow, label: 'Release Gate' },
    ],
  },
];

export function getCurrentPage(pathname: string, search: string): { group?: NavGroup; item?: NavItem } {
  const tab = new URLSearchParams(search).get('tab') ?? '';
  const links = GROUPS.flatMap((group) => group.items.map((item) => ({ group, item })));
  const matches = links.filter(({ item }) => matchPath({ path: item.to.split('?')[0], end: false }, pathname));
  return matches.find(({ item }) => item.tabs?.includes(tab))
    ?? matches.find(({ item }) => !item.tabs)
    ?? {};
}

export function Sidebar() {
  const { pathname, search } = useLocation();
  const { item: currentItem } = getCurrentPage(pathname, search);
  return (
    <aside className="glass-strong z-10 max-h-[45dvh] shrink-0 overflow-y-auto border-b border-white/10 md:max-h-none md:w-56 md:border-b-0 md:border-r">
      <div className="flex h-14 items-center gap-3 px-4 md:h-16">
        <img src="/brainwave-logo.png" width="40" height="40" className="h-10 w-10 rounded-lg object-cover" alt="" />
        <span className="font-display text-lg font-bold tracking-tight neon-text">Brainwave Eval</span>
      </div>
      <nav aria-label="Eval Lab sections" className="grid grid-cols-2 gap-x-3 gap-y-4 px-3 pb-4 md:block md:space-y-5 md:pt-3">
        {GROUPS.map(({ id, label, items }) => (
          <section key={id} aria-labelledby={id}>
            <h2 id={id} className="mb-1.5 border-b border-white/10 px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              {label}
            </h2>
            <ul className="space-y-0.5">
              {items.map(({ to, icon: Icon, label: name }) => (
                <li key={to}>
                  <Link
                    to={to}
                    aria-current={to === currentItem?.to ? 'page' : undefined}
                    className={cn(
                      'flex min-h-9 items-center gap-2.5 rounded-md border-l-2 px-2 py-1.5 text-xs font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-neon md:text-sm',
                      to === currentItem?.to
                        ? 'border-neon bg-neon/10 text-neon'
                        : 'border-transparent text-muted-foreground hover:bg-white/5 hover:text-foreground',
                    )}
                  >
                    <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
                    {name}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </nav>
    </aside>
  );
}
