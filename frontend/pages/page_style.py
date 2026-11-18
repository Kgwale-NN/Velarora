"""Shared local font, loading skeleton and gentle page transitions."""
from nicegui import ui
from frontend.pages.design_assets import asset_url, stylesheet


def page_style(kind: str):
    ui.colors(primary="#ffffff0d", secondary="#c9c9c9", accent="#a1a1a1",
              dark="#181818", dark_page="#060607")
    ui.add_head_html('<link rel="preload" href="/design-assets/fonts/cormorant-normal-400.woff2" as="font" type="font/woff2" crossorigin>')
    stylesheet("page-style.css")
    stylesheet("glass-motion.css")
    stylesheet("glass-controls.css")
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
    ui.add_head_html(f'<script src="{asset_url("dialog-events.js")}" defer></script>')
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
                !['/','/history','/analytics','/reports','/alerts','/groups','/schedules','/users','/models','/audit','/profile','/teacher-profile','/settings','/login'].includes(next.pathname)) return;
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
