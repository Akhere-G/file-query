import type { Metadata } from "next";
import { Geist, Geist_Mono, Noto_Sans, Quicksand } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import Header from "@/components/common/Header";
import Footer from "@/components/common/Footer";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/common/Appsidebar";
import { ThemeSync } from "@/components/common/ThemeSync";
import { cookies } from "next/headers";

const playfairDisplayHeading = Quicksand({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["300", "400", "500", "600", "700"],
});

const notoSans = Noto_Sans({ subsets: ["latin"], variable: "--font-sans" });

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "FileQuery | Intelligent Document Management",
    template: "%s | FileQuery",
  },
  description:
    "A fullstack platform built to ingest, process, and query your knowledge base using cutting-edge RAG techniques and hybrid search.",
  keywords: [
    "RAG AI",
    "Document Search",
    "Vector Database",
    "Knowledge Management",
    "Hybrid Search",
    "LangChain",
  ],
  authors: [{ name: "Akhere" }],
  creator: "Akhere",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://file-query-frontend-752853711822.europe-west1.run.app",
    title: "FileQuery | Intelligent Document Management",
    description:
      "A fullstack platform built to ingest, process, and query your knowledge base using cutting-edge RAG techniques and hybrid search.",
    siteName: "FileQuery",
    images: [
      {
        url: "https://file-query-frontend-752853711822.europe-west1.run.app/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "FileQuery Platform",
      },
    ],
  },
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const defaultLinks = [{ name: "Projects", href: "/dashboard" }];

  const authLinks = [{ name: "Settings", href: "/settings" }];
  const guestLinks = [
    { name: "Login", href: "/login" },
    { name: "Register", href: "/register" },
  ];
  const footerLinks = [
    {
      title: "Product",
      links: [
        { name: "Dashboard", href: "/dashboard" },
        { name: "Features", href: "/features" },
      ],
    },
    {
      title: "Company",
      links: [
        { name: "About", href: "/" },
        { name: "Contact", href: "/" },
      ],
    },
    {
      title: "Legal",
      links: [
        { name: "Privacy", href: "/privacy" },
        { name: "Terms", href: "/terms" },
      ],
    },
  ];
  const cookieStore = await cookies();
  const isAuth = !!cookieStore.get("access_token");
  const links = isAuth
    ? defaultLinks.concat(authLinks)
    : defaultLinks.concat(guestLinks);

  return (
    <html
      lang="en"
      className={cn(
        "h-full",
        "antialiased",
        geistSans.variable,
        geistMono.variable,
        "font-sans",
        notoSans.variable,
        playfairDisplayHeading.variable,
      )}
    >
      <body className="min-h-full flex flex-col">
        <ThemeSync />
        <SidebarProvider defaultOpen={false}>
          <div className="w-screen">
            <Header links={links} isAuth={isAuth} />

            {children}
            <AppSidebar links={links} isAuth={isAuth} />
            <Footer groups={footerLinks} />
          </div>
        </SidebarProvider>
      </body>
    </html>
  );
}
