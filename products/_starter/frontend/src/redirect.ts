/**
 * Leave the SPA for a provider-supplied URL (Stripe checkout or portal, or the mock's own page).
 * Only https: URLs and same-origin URLs (the mock's path) are followed; anything else
 * (javascript:, data:, http://other-host, //other-host) is refused so a wrong provider reply or
 * config can never run script or send the user to a plain-http site.
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
  window.location.assign(url);
  return true;
}

export const BAD_REDIRECT = "We got an unexpected billing link and didn't follow it. Please try again or contact support.";
