"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SidebarTrigger } from "../ui/sidebar";

interface HeaderProps {
  links: { name: string; href: string }[];
}
export default function Header({ links }: HeaderProps) {
  const pathname = usePathname();

  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <Link href="/">
          <h1 className="text-2xl font-bold tracking-tighter">
            File<span className="text-primary">Query</span>
          </h1>
        </Link>

        <nav className="hidden md:block">
          <ul className="flex items-center gap-6">
            {links.map(({ name, href }) => (
              <li key={href}>
                <Link
                  href={href}
                  className={`text-sm font-medium transition-colors hover:text-primary ${
                    pathname === href
                      ? "text-primary"
                      : "text-secondary-foreground"
                  }`}
                >
                  {name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="md:hidden">
          <SidebarTrigger />
        </div>
      </div>
    </header>
  );
}
