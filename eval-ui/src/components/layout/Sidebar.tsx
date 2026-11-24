import { useState, type ElementType } from 'react';
import { Link, matchPath, useLocation } from 'react-router-dom';
import {
  ChevronDown, Database, FlaskConical, Gavel, GitPullRequestArrow,
  Languages, MessageSquareQuote, Scale, Search, ShieldCheck, Sigma,
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
  icon: ElementType;
  items: NavItem[];
}

const GROUPS: NavGroup[] = [
  {
    id: 'data-experiments',
    label: 'Data & Experiments',
    icon: Database,
    items: [
      { to: '/evaluation/dataset', icon: Database, label: 'Golden Sets' },
      { to: '/evaluation/normalization', icon: Languages, label: 'Arabic Normalization' },
      { to: '/evaluation/retrieval?tab=score', icon: Search, label: 'Retrieval Evaluation', tabs: ['score', 'compare'] },
      { to: '/evaluation/generation?tab=pipeline', icon: MessageSquareQuote, label: 'Generation Evaluation', tabs: ['pipeline', 'components', 'compare'] },
      { to: '/evaluation/experiments', icon: Scale, label: 'Retrieval Experiments' },
      { to: '/evaluation/judges', icon: Gavel, label: 'Judge Calibration' },
    ],
  },
  {
    id: 'playground',
    label: 'Playground',
    icon: FlaskConical,
    items: [
      { to: '/evaluation/retrieval', icon: Search, label: 'Retrieval Probe' },
      { to: '/evaluation/generation', icon: FlaskConical, label: 'RAGAS Metrics' },
      { to: '/evaluation/stats', icon: Sigma, label: 'Statistics Lab' },
    ],
  },
  {
    id: 'release-operations',
    label: 'Release Operations',
    icon: ShieldCheck,
    items: [
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
  const { pathname, search, key } = useLocation();
  const { group: currentGroup, item: currentItem } = getCurrentPage(pathname, search);
  const [toggle, setToggle] = useState<{ key: string; openId: string | null }>();
  const openId = toggle?.key === key ? toggle.openId : currentGroup?.id;

  return (
    <aside className="glass-strong z-10 max-h-[45dvh] shrink-0 overflow-y-auto border-b border-white/10 md:max-h-none md:w-56 md:border-b-0 md:border-r">
      <div className="flex h-14 items-center gap-3 px-4 md:h-16">
        <img src="/brainwave-logo.png" width="40" height="40" className="h-10 w-10 rounded-lg object-cover" alt="" />
        <span className="font-display text-lg font-bold tracking-tight neon-text">Brainwave Eval</span>
      </div>
      <nav aria-label="Eval Lab sections" className="space-y-1.5 px-3 pb-3 md:pt-4">
        {GROUPS.map(({ id, label, icon: Icon, items }) => {
          const open = openId === id;
          return (
            <div key={id}>
              <button
                type="button"
                aria-expanded={open}
                aria-controls={`nav-${id}`}
                onClick={() => setToggle({ key, openId: open ? null : id })}
                className={cn(
                  'flex min-h-10 w-full items-center gap-2.5 rounded-lg border border-white/10 bg-white/[0.025] px-2.5 text-left text-sm font-medium hover:border-white/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-neon',
                  currentGroup?.id === id ? 'text-neon' : 'text-foreground',
                )}
              >
                <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
                <span className="flex-1">{label}</span>
                <ChevronDown aria-hidden="true" className={cn('h-4 w-4 shrink-0 text-muted-foreground motion-safe:transition-transform', open && 'rotate-180')} />
              </button>
              <ul id={`nav-${id}`} hidden={!open} className="ml-2.5 mt-1 space-y-0.5 border-l border-white/10 pl-2">
                {items.map(({ to, icon: ItemIcon, label }) => {
                  const active = to === currentItem?.to;
                  return (
                    <li key={to}>
                      <Link
                        to={to}
                        aria-current={active ? 'page' : undefined}
                        className={cn(
                          'flex min-h-9 items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-neon',
                          active ? 'bg-neon/10 text-neon' : 'text-muted-foreground hover:bg-white/5 hover:text-foreground',
                        )}
                      >
                        <ItemIcon aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
                        {label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
