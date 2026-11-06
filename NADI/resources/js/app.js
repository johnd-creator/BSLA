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
