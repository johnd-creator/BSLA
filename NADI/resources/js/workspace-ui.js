// Progressive enhancements only. Navigation, disclosure, filters and forms also work without JavaScript.
export const errorFieldName = (name) => name.split('.').reduce((result, part, index) => index ? `${result}[${part}]` : part, '');

export const isEditing = (target) => Boolean(target?.closest?.('input, textarea, select, [contenteditable=true], [role=textbox]'));

export function setupWorkspace(document, window) {
    const mobile = window.matchMedia('(max-width: 700px)');
    document.querySelectorAll('[data-mobile-filters]').forEach((details) => {
        const sync = () => { details.open = !mobile.matches || details.dataset.active === 'true'; };
        sync();
        mobile.addEventListener('change', sync);
    });

    const search = document.querySelector('[data-search-input], .filters input[name=q]');
    if (search) {
        document.addEventListener('keydown', (event) => {
            if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey || isEditing(event.target)) return;
            event.preventDefault();
            search.focus();
        });
    }

    // Focusable regions and scroll cues are exposed only when scrolling is useful.
    const tableRegions = [...document.querySelectorAll('.table-scroll')].map((region) => {
        const hint = document.createElement('div');
        hint.className = 'table-scroll-hint';
        hint.textContent = 'Geser tabel untuk melihat kolom lainnya →';
        hint.hidden = true;
        region.before(hint);
        const heading = region.closest('.panel')?.querySelector('h2, h3');
        const name = heading?.textContent.trim() || region.getAttribute('aria-label') || 'Tabel data';
        const sync = () => {
            const horizontal = region.scrollWidth > region.clientWidth + 1;
            const scrollable = horizontal || region.scrollHeight > region.clientHeight + 1;
            hint.hidden = !horizontal;
            if (scrollable) {
                region.tabIndex = 0;
                region.setAttribute('role', 'region');
                region.setAttribute('aria-label', `${name}, dapat digulir`);
            } else {
                region.removeAttribute('tabindex');
                region.removeAttribute('role');
                region.removeAttribute('aria-label');
            }
        };
        sync();
        return { region, sync };
    });
    if (window.ResizeObserver) {
        const observer = new window.ResizeObserver(() => tableRegions.forEach(({ sync }) => sync()));
        tableRegions.forEach(({ region }) => observer.observe(region));
    } else {
        window.addEventListener('resize', () => tableRegions.forEach(({ sync }) => sync()));
    }

    const summary = document.querySelector('[data-error-summary]');
    if (summary) {
        const findField = (key) => document.getElementsByName(errorFieldName(key))[0]
            || document.getElementsByName(`${key}[]`)[0];
        summary.querySelectorAll('[data-error-field]').forEach((link) => {
            const field = findField(link.dataset.errorField);
            if (!field || field.type === 'hidden') return;
            field.setAttribute('aria-invalid', 'true');
            const error = document.getElementById(link.hash.slice(1));
            if (error) {
                const described = new Set((field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
                described.add(error.id);
                field.setAttribute('aria-describedby', [...described].join(' '));
            }
            link.addEventListener('click', (event) => {
                event.preventDefault();
                let ancestor = field.parentElement;
                while (ancestor) {
                    if (ancestor.tagName === 'DETAILS') ancestor.open = true;
                    ancestor = ancestor.parentElement;
                }
                field.focus();
                field.scrollIntoView({ block: 'center' });
            });
        });
        summary.focus({ preventScroll: true });
    }

    // Keep repeated clicks from submitting a local editing form twice. Server-side checks remain authoritative.
    const forms = [...document.querySelectorAll('form.form-panel[method=post]')];
    forms.forEach((form) => {
        form.addEventListener('submit', (event) => {
            if (form.dataset.submitting === 'true') {
                event.preventDefault();
                return;
            }
            form.dataset.submitting = 'true';
            form.setAttribute('aria-busy', 'true');
            form.querySelectorAll('button[type=submit]').forEach((button) => {
                button.dataset.originalLabel = button.textContent;
                button.textContent = 'Menyimpan…';
                button.disabled = true;
            });
        });
    });
    window.addEventListener('pageshow', () => forms.forEach((form) => {
        delete form.dataset.submitting;
        form.removeAttribute('aria-busy');
        form.querySelectorAll('button[data-original-label]').forEach((button) => {
            button.textContent = button.dataset.originalLabel;
            button.disabled = false;
            delete button.dataset.originalLabel;
        });
    }));

    const navigation = document.querySelector('.navigation');
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && mobile.matches && navigation?.open) {
            navigation.open = false;
            navigation.querySelector('summary')?.focus();
        }
    });
}
