import Link from "next/link";
import { CookiePreferencesButton } from "@/components/common/CookieConsent";

type FooterLink = {
  name: string;
  href: string;
};

type FooterLinkGroup = {
  title: string;
  links: FooterLink[];
};

type FooterProps = {
  groups: FooterLinkGroup[];
};

export default function Footer({ groups }: FooterProps) {
  return (
    <footer className="border-t bg-card">
      <div className="mx-auto max-w-7xl px-4 py-10">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {groups.map((group) => (
            <div key={group.title}>
              <h3 className="mb-4 text-sm font-semibold">{group.title}</h3>

              <ul className="space-y-3">
                {group.links.map((link) => (
                  <li key={link.name}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} FileQuery. All rights reserved.
          </p>
          <CookiePreferencesButton
            variant="link"
            className="h-auto justify-start p-0 text-xs sm:justify-center"
          />
        </div>
      </div>
    </footer>
  );
}
