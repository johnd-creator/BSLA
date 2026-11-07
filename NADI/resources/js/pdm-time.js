// Keep unknown time genuinely absent. Disabled fields are not posted, while
// values remain available if the user changes the precision selector and back.
export function setupPdmTime(section) {
    const precision = section.querySelector('[name="time_precision"]');
    const sync = () => {
        section.querySelectorAll('[data-time-fields]').forEach((group) => {
            const active = group.dataset.timeFields === precision.value;
            group.hidden = !active;
            group.querySelectorAll('input, select').forEach((input) => {
                input.disabled = !active;
                input.required = active;
            });
        });
    };
    precision.addEventListener('change', sync);
    sync();
}
