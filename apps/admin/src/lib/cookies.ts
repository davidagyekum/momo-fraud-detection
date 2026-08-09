export function readCookie(
  name: string,
  cookieHeader = document.cookie,
): string | null {
  const encodedName = `${encodeURIComponent(name)}=`;
  for (const segment of cookieHeader.split(";")) {
    const candidate = segment.trim();
    if (candidate.startsWith(encodedName)) {
      return decodeURIComponent(candidate.slice(encodedName.length));
    }
  }
  return null;
}
