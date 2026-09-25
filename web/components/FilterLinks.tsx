import Link from "next/link";

type Props = { base: string; param: string; options: [string, string][]; current?: string };

export default function FilterLinks({ base, param, options, current }: Props) {
  const cls = (active: boolean) =>
    `rounded px-2 py-1 ${active ? "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900" : "border"}`;
  return (
    <nav className="mb-4 flex flex-wrap gap-2 text-sm">
      <Link href={base} className={cls(!current)}>전체</Link>
      {options.map(([value, label]) => (
        <Link key={value} href={`${base}?${param}=${encodeURIComponent(value)}`} className={cls(current === value)}>
          {label}
        </Link>
      ))}
    </nav>
  );
}
