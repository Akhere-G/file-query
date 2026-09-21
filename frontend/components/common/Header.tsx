"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SidebarTrigger } from "../ui/sidebar";
import { Button } from "../ui/button";
import { logout } from "@/features/auth/api/authApi";

interface HeaderProps {
  links: { name: string; href: string }[];
  isAuth: boolean;
}
export default function Header({ links, isAuth }: HeaderProps) {
  const pathname = usePathname();

  async function logoutFn() {
    await logout();
    window.location.reload();
  }

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
            {isAuth && (
              <li>
                <Button variant="ghost" className="p-0" onClick={logoutFn}>
                  Log out
                </Button>
              </li>
            )}
          </ul>
        </nav>

        <div className="md:hidden">
          <SidebarTrigger />
        </div>
      </div>
    </header>
  );
}
