"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { logout } from "@/features/auth/api/authApi";

interface AppSidebarProps {
  links: { name: string; href: string; icon?: React.ReactNode }[];
  isAuth: boolean;
}
export function AppSidebar({ links, isAuth }: AppSidebarProps) {
  const pathname = usePathname();

  async function logoutFn() {
    await logout();
    window.location.reload();
  }

  return (
    <Sidebar collapsible="offcanvas" side="right">
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="mb-2">
            <Link href="/">
              <h1 className="text-xl font-bold tracking-tighter">
                File<span className="text-primary">Query</span>
              </h1>
            </Link>
          </SidebarGroupLabel>

          <SidebarGroupContent>
            <SidebarMenu>
              {links.map(({ name, href, icon: Icon }) => (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton
                    isActive={pathname === href}
                    tooltip={name}
                  >
                    <Link
                      href={href}
                      className={` w-100 h-100 -mx-3 px-3 flex items-center gap-2 hover:text-primary ${pathname === href ? "text-primary" : ""}`}
                    >
                      {Icon}
                      <span>{name}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}

              {isAuth && (
                <SidebarMenuItem>
                  <SidebarMenuButton className="px-3" onClick={logoutFn}>
                    Log out
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
