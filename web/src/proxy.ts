import { NextResponse, type NextRequest } from "next/server";

/**
 * Optimistic auth check: send visitors without a session cookie to sign in.
 * The API still verifies the signed cookie on every request.
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.has("pd_session");
  const isAuthPage = ["/login", "/signup", "/forgot", "/reset"].includes(pathname);

  if (!hasSession && !isAuthPage) {
    const url = new URL("/login", request.url);
    if (pathname !== "/") url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|ico)$).*)"],
};
