import { Button } from '@/components/ui/button';

interface Props {
  title?: string;
  motion: boolean;
  toggleMotion(): void;
}

export function Header({ title, motion, toggleMotion }: Props) {
  return (
    <header className="glass z-[5] flex h-16 items-center justify-between border-b border-white/5 px-4">
      <div className="flex items-center gap-3">
        {title && (
          <div className="flex items-center gap-2">
            <span className="h-4 w-px bg-gradient-to-b from-transparent via-neon/60 to-transparent" />
            <h1 className="font-display text-sm font-semibold tracking-wide text-foreground">
              {title}
            </h1>
          </div>
        )}
      </div>

      <Button variant="ghost" size="sm" onClick={toggleMotion} aria-pressed={motion}>{motion ? 'Pause motion' : 'Enable motion'}</Button>
    </header>
  );
}
