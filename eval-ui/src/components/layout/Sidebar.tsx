import { NavLink } from 'react-router-dom';
import { Database, Search, Scale, Sigma, MessageSquareQuote, Gavel, GitPullRequestArrow, Languages } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem { to: string; icon: React.ElementType; label: string }

const EVALUATION: NavItem[] = [
  { to: '/evaluation/dataset',     icon: Database,      label: 'Golden Sets'   },
  { to: '/evaluation/retrieval',   icon: Search,        label: 'Retrieval'     },
  { to: '/evaluation/normalization', icon: Languages,   label: 'Arabic Norm'    },
  { to: '/evaluation/experiments', icon: Scale,         label: 'Experiments'   },
  { to: '/evaluation/stats',       icon: Sigma,         label: 'Stats Lab'     },
  { to: '/evaluation/generation',  icon: MessageSquareQuote, label: 'Generation' },
  { to: '/evaluation/judges',      icon: Gavel,         label: 'Judge Lab'     },
  { to: '/evaluation/gate',        icon: GitPullRequestArrow, label: 'Release Gate' },
];

export function Sidebar() {
  return (
    <aside className="glass-strong z-10 shrink-0 border-b border-white/10 md:w-56 md:overflow-y-auto md:border-b-0 md:border-r">
      <div className="flex h-14 items-center gap-3 px-4 md:h-16">
        <img src="/brainwave-logo.png" width="40" height="40" className="h-10 w-10 rounded-lg object-cover" alt="" />
        <span className="font-display text-lg font-bold tracking-tight neon-text">Brainwave Eval</span>
      </div>
      <nav aria-label="Eval Lab sections" className="grid grid-cols-2 gap-1.5 px-3 pb-3 min-[380px]:grid-cols-3 sm:grid-cols-4 md:grid-cols-1 md:gap-2 md:pt-4">
        {EVALUATION.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} className={({ isActive }) => cn(
            'flex min-h-9 items-center gap-2 rounded-full border px-2.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-neon md:min-h-11 md:gap-3 md:px-4 md:text-sm',
            isActive ? 'border-neon/50 bg-neon/10 text-neon' : 'border-white/10 bg-white/[0.025] text-muted-foreground hover:border-white/25 hover:text-foreground',
          )}>
            <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
