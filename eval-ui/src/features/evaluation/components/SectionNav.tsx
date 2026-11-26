import type { ElementType } from 'react';

export function SectionNav<T extends string>({ label, items, value, onChange }: {
  label: string;
  items: readonly { id: T; title: string; icon?: ElementType }[];
  value: T;
  onChange: (id: T) => void;
}) {
  return <nav aria-label={label} className="lab-sections">
    {items.map(({id, title, icon: Icon}) => (
      <button type="button" key={id} aria-current={value === id ? 'page' : undefined}
        onClick={() => onChange(id)}>
        {Icon && <Icon size={15} aria-hidden="true" />}{title}
      </button>
    ))}
  </nav>;
}
