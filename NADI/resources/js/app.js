import { setupRepairIntervals } from './reliability-intervals';
import { setupHistorian } from './historian-demand';
import { setupCems } from './cems-live';
import { setupWorkspace } from './workspace-ui';
import { setupPdmTime } from './pdm-time';

document.querySelectorAll('[data-pdm-time]').forEach(setupPdmTime);

// Use native disclosure behavior on mobile; keep desktop navigation visible.
const navigation = document.querySelector('.navigation');

if (navigation) {
    const mobile = window.matchMedia('(max-width: 700px)');
    const syncNavigation = () => {
        navigation.open = !mobile.matches;
    };

    syncNavigation();
    mobile.addEventListener('change', syncNavigation);
}

if (document.documentElement) setupWorkspace(document, window);

document.querySelectorAll('[data-cems]').forEach((root) => setupCems(root));

document.querySelectorAll('[data-historian]').forEach((root) => setupHistorian(root));

document.querySelectorAll('[data-repair-intervals]').forEach(setupRepairIntervals);
