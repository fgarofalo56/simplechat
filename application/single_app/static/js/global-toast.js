// global-toast.js
// Global toast notification utility - replaces native alert() calls with Bootstrap toasts.
// Loaded in base.html before other scripts so it's available everywhere.

(function() {
    'use strict';

    /**
     * Show a Bootstrap toast notification.
     * @param {string} message - The message to display
     * @param {string} variant - Bootstrap color variant: 'success', 'danger', 'warning', 'info' (default: 'info')
     * @param {number} duration - Auto-hide delay in ms (default: 5000)
     */
    window.showGlobalToast = function(message, variant, duration) {
        variant = variant || 'info';
        duration = duration || 5000;

        var container = document.getElementById('toast-container');
        if (!container) {
            // Fallback: create container if missing
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'position-fixed bottom-0 end-0 p-3';
            container.style.zIndex = '1100';
            document.body.appendChild(container);
        }

        var iconMap = {
            success: 'bi-check-circle-fill',
            danger: 'bi-x-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill'
        };
        var icon = iconMap[variant] || iconMap.info;

        var toastEl = document.createElement('div');
        toastEl.className = 'toast align-items-center text-bg-' + variant + ' border-0';
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML =
            '<div class="d-flex">' +
                '<div class="toast-body">' +
                    '<i class="bi ' + icon + ' me-2"></i>' +
                    message +
                '</div>' +
                '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
            '</div>';

        container.appendChild(toastEl);

        var toast = new bootstrap.Toast(toastEl, { delay: duration });
        toast.show();

        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    };

    /**
     * Show a Bootstrap modal confirmation dialog (replaces native confirm()).
     * Returns a Promise that resolves to true (confirmed) or false (cancelled).
     * @param {string} message - Confirmation message
     * @param {string} title - Modal title (default: 'Confirm')
     * @param {string} confirmText - Confirm button text (default: 'Confirm')
     * @param {string} variant - Button variant: 'danger', 'primary', 'warning' (default: 'danger')
     * @returns {Promise<boolean>}
     */
    window.showGlobalConfirm = function(message, title, confirmText, variant) {
        title = title || 'Confirm';
        confirmText = confirmText || 'Confirm';
        variant = variant || 'danger';

        return new Promise(function(resolve) {
            // Remove any existing confirm modal
            var existing = document.getElementById('globalConfirmModal');
            if (existing) existing.remove();

            var modalEl = document.createElement('div');
            modalEl.id = 'globalConfirmModal';
            modalEl.className = 'modal fade';
            modalEl.setAttribute('tabindex', '-1');
            modalEl.innerHTML =
                '<div class="modal-dialog modal-dialog-centered">' +
                    '<div class="modal-content">' +
                        '<div class="modal-header">' +
                            '<h5 class="modal-title">' + title + '</h5>' +
                            '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>' +
                        '</div>' +
                        '<div class="modal-body"><p>' + message + '</p></div>' +
                        '<div class="modal-footer">' +
                            '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>' +
                            '<button type="button" class="btn btn-' + variant + '" id="globalConfirmBtn">' + confirmText + '</button>' +
                        '</div>' +
                    '</div>' +
                '</div>';

            document.body.appendChild(modalEl);
            var modal = new bootstrap.Modal(modalEl);

            var resolved = false;

            var confirmBtn = document.getElementById('globalConfirmBtn');
            confirmBtn.addEventListener('click', function() {
                resolved = true;
                modal.hide();
                resolve(true);
            });

            modalEl.addEventListener('hidden.bs.modal', function() {
                modalEl.remove();
                if (!resolved) {
                    resolve(false); // If closed without confirming
                }
            });

            modal.show();
        });
    };
})();
