import Link from "next/link";

type Props = { base: string; param: string; options: [string, string][]; current?: string };

export default function FilterLinks({ base, param, options, current }: Props) {
  const cls = (active: boolean) =>
    `rounded-full border px-3 py-1 ${
      active ? "border-foreground bg-foreground text-background" : "border-line text-muted hover:text-foreground"
    }`;
  return (
    <nav className="mb-6 flex flex-wrap gap-2 text-sm">
      <Link href={base} className={cls(!current)}>전체</Link>
      {options.map(([value, label]) => (
        <Link key={value} href={`${base}?${param}=${encodeURIComponent(value)}`} className={cls(current === value)}>
          {label}
        </Link>
      ))}
    </nav>
  );
}
