"""Shared local font, loading skeleton and gentle page transitions."""
from pathlib import Path
from nicegui import app, ui

ASSETS = Path(__file__).parents[1] / "assets"
app.add_static_files("/design-assets", str(ASSETS))


def page_style(kind: str):
    ui.add_css((ASSETS / "page-style.css").read_text())
    ui.add_body_html(f"""
        <div class="page-loading loading-{kind}" role="status" aria-label="Loading page">
            <span class="loading-sr-only">Loading page</span>
            <div class="loading-top"><i></i><i></i></div>
            <div class="loading-panel">
                <i class="loading-heading"></i><i class="loading-short"></i>
                <div class="loading-fields"><i></i><i></i><i></i><i></i></div>
                <i class="loading-button"></i>
            </div>
        </div>
    """)
    ui.add_head_html("""
        <script>
        document.documentElement.classList.remove('velarora-ready');
        document.addEventListener('click', (event) => {
            const link = event.target.closest('a[href]');
            if (!link || event.defaultPrevented || event.ctrlKey || event.metaKey ||
                event.shiftKey || event.altKey || event.button !== 0 ||
                link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
            const next = new URL(link.href, location.href);
            if (next.origin !== location.origin || next.pathname === location.pathname ||
                !['/users','/models','/audit','/profile','/settings','/login'].includes(next.pathname)) return;
            document.documentElement.classList.remove('velarora-ready');
        });
        window.addEventListener('pageshow', (event) => {
            if (event.persisted) document.documentElement.classList.add('velarora-ready');
        });
        </script>
    """)
    ui.context.client.on_connect(lambda: ui.run_javascript("""
        requestAnimationFrame(() => requestAnimationFrame(() => {
            document.documentElement.classList.add('velarora-ready');
        }));
    """))
