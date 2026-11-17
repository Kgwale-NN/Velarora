document.addEventListener('contextmenu', (event) => {
    const dialog = event.target.closest('.q-dialog');
    if (!dialog) return;
    const content = dialog.querySelector('.q-dialog__inner')?.firstElementChild;
    if (content?.contains(event.target)) {
        event.stopPropagation();
        return;
    }
    const backdrop = dialog.querySelector('.q-dialog__backdrop');
    if (backdrop) {
        event.preventDefault();
        backdrop.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, button: 0}));
    }
});
