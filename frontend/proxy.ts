import { NextRequest, NextResponse } from "next/server";
import { jwtDecode } from "jwt-decode";

type JwtPayload = {
  exp?: number;
};

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  let token: string | null | undefined =
    request.cookies.get("access_token")?.value;
  let tokenExpired = false;

  if (token) {
    try {
      const value = jwtDecode<JwtPayload>(token);

      const exp = (value.exp ?? 0) * 1000;
      tokenExpired = exp <= Date.now();

      if (tokenExpired) {
        token = null;
      }
    } catch {
      token = null;
      tokenExpired = true;
    }
  }

  const guestPaths = ["/login", "/register"];
  const protectedPaths = ["/dashboard", "/settings"];

  const isGuestPage = guestPaths.some((path) => pathname === path);

  const isProtectedPage = protectedPaths.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  let response: NextResponse;

  if (isProtectedPage && !token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);

    response = NextResponse.redirect(loginUrl);
  } else if (isGuestPage && token) {
    response = NextResponse.redirect(new URL("/dashboard", request.url));
  } else {
    response = NextResponse.next();
  }

  if (tokenExpired) {
    response.cookies.delete("access_token");
  }

  return response;
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
