// navigator.clipboard.writeText silently rejects (or doesn't exist at all)
// on an insecure origin - the same "http://<LAN-IP>:3000 isn't https or
// localhost" restriction that blocks camera access elsewhere in this app.
// Falls back to the old execCommand('copy') trick, which still works in
// more places, and always resolves to a real true/false instead of leaving
// the caller to guess whether anything happened.
export async function copyToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // fall through to the legacy path below
    }
  }

  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}
