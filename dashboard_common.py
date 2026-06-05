"""
dashboard_common.py - Shared building blocks for the dashboard generators.

The two dashboards (build_dashboard.py, build_manuals_dashboard.py) have
genuinely different layouts/CSS, so they are not collapsed into one template.
What they MUST share is the client-side security code (renderDiff()'s allow-list
has to stay in lockstep with the diff tags emitted by scraper.diff_texts()) and
the way untrusted data is embedded into the page — so both live here as a single
source of truth.
"""
import json

# Injected into each dashboard's <script> via the __SECURITY_JS__ placeholder.
# esc() escapes raw values for innerHTML; renderDiff() permits ONLY the four
# diff tags emitted by scraper.diff_texts() and escapes everything else, so even
# diff HTML written by older runs cannot inject markup. safeUrl() blocks non
# http(s) URLs (e.g. javascript:) so a poisoned link can't execute. Keep the tag
# strings in DIFF_RE/DIFF_TAGS identical to those produced by diff_texts().
SECURITY_JS = r"""
        // --- XSS hardening ------------------------------------------------
        // PDF-extracted text is untrusted. esc() escapes raw values for
        // innerHTML; renderDiff() permits ONLY the four diff tags emitted by
        // diff_texts() and escapes everything else, so even diff HTML written
        // by older runs cannot inject markup. safeUrl() rejects non-http(s)
        // URLs so a poisoned link cannot run javascript: on click.
        const esc = (s) => s == null ? '' : String(s).replace(/[&<>"']/g,
            c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        const safeUrl = (u) => /^https?:\/\//i.test(String(u || '')) ? String(u) : '#';
        const DIFF_RE = /(<del style="color: #9ca3af;">|<\/del>|<b style="color: #ea580c; background: #ffedd5;">|<\/b>)/g;
        const DIFF_TAGS = new Set(['<del style="color: #9ca3af;">', '</del>',
            '<b style="color: #ea580c; background: #ffedd5;">', '</b>']);
        const renderDiff = (s) => s == null ? '' :
            String(s).split(DIFF_RE).map(p => DIFF_TAGS.has(p) ? p : esc(p)).join('');""".lstrip("\n")


def embed_json(data):
    """
    Serialise data for safe inlining inside a <script> tag.

    Beyond plain json.dumps, this escapes the characters that could otherwise
    let attacker-controlled string values break out of the script element or the
    surrounding JS string: '<', '>', '&' become \\u-escapes (neutralising
    </script>, <!--, <script ...), and U+2028/U+2029 are escaped because they
    are illegal raw in JS string literals. The result is still valid JSON/JS.
    """
    bs = "\\"  # a single backslash; keeps the escapes below unambiguous
    s = json.dumps(data, ensure_ascii=False)
    return (s.replace("<", bs + "u003c")
             .replace(">", bs + "u003e")
             .replace("&", bs + "u0026")
             .replace(chr(0x2028), bs + "u2028")
             .replace(chr(0x2029), bs + "u2029"))
