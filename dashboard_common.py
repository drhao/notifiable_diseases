"""
dashboard_common.py - Shared building blocks for the dashboard generators.

The two dashboards (build_dashboard.py, build_manuals_dashboard.py) have
genuinely different layouts/CSS, so they are not collapsed into one template.
What they MUST share is the client-side security code: renderDiff()'s allow-list
has to stay in lockstep with the diff tags emitted by scraper.diff_texts(), so
both pages inject the exact same helpers from here (single source of truth).
"""

# Injected into each dashboard's <script> via the __SECURITY_JS__ placeholder.
# esc() escapes raw values for innerHTML; renderDiff() permits ONLY the four
# diff tags emitted by scraper.diff_texts() and escapes everything else, so even
# diff HTML written by older runs cannot inject markup. Keep the tag strings in
# DIFF_RE/DIFF_TAGS identical to those produced by diff_texts().
SECURITY_JS = """\
        // --- XSS hardening ------------------------------------------------
        // PDF-extracted text is untrusted. esc() escapes raw values for
        // innerHTML; renderDiff() permits ONLY the four diff tags emitted by
        // diff_texts() and escapes everything else, so even diff HTML written
        // by older runs cannot inject markup.
        const esc = (s) => s == null ? '' : String(s).replace(/[&<>"']/g,
            c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        const DIFF_RE = /(<del style="color: #9ca3af;">|<\\/del>|<b style="color: #ea580c; background: #ffedd5;">|<\\/b>)/g;
        const DIFF_TAGS = new Set(['<del style="color: #9ca3af;">', '</del>',
            '<b style="color: #ea580c; background: #ffedd5;">', '</b>']);
        const renderDiff = (s) => s == null ? '' :
            String(s).split(DIFF_RE).map(p => DIFF_TAGS.has(p) ? p : esc(p)).join('');"""
