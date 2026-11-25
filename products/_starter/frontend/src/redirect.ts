/**
 * Leave the SPA for a provider-supplied URL (Stripe checkout or portal, or the mock's own page).
 * Only https: URLs and same-origin URLs (the mock's path) are followed; anything else
 * (javascript:, data:, a plain-http URL on another host) is refused so a wrong provider reply or
 * config can never run script or send the user to a plain-http site.
 * Protocol-relative (//host) and backslash (/\host, \\host) URLs inherit the page's scheme: on an https
 * origin (production) they are https URLs and are followed like any other https URL (this is a scheme
 * guarantee, not a host allowlist); on an http dev origin they become http://host and are refused.
 * The browser is sent to the parsed URL (target.href), so what was checked is what is followed.
 * Returns true if it navigated, false if the URL was refused.
 */
export function safeRedirect(url: string): boolean {
  let target: URL;
  try {
    target = new URL(url, window.location.origin);
  } catch {
    return false;
  }
  if (target.protocol !== "https:" && target.origin !== window.location.origin) return false;
  window.location.assign(target.href);
  return true;
}

export const BAD_REDIRECT = "We got an unexpected billing link and didn't follow it. Please try again or contact support.";
