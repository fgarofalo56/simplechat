// api-client.js
// Shared fetch wrapper with automatic CSRF token injection, error handling,
// and toast notifications. Replaces ad-hoc fetch calls across the codebase.
//
// Usage:
//   import { apiFetch, apiGet, apiPost, apiPut, apiDelete } from '/static/js/utils/api-client.js';
//
//   const { ok, status, data, error } = await apiGet('/api/documents');
//   const result = await apiPost('/api/documents', { name: 'test.pdf' });

/**
 * Get the CSRF token from the meta tag in base.html.
 * @returns {string} The CSRF token, or empty string if not found.
 */
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

/**
 * Shared fetch wrapper with consistent error handling.
 *
 * @param {string} url - The URL to fetch.
 * @param {object} [options={}] - Fetch options (method, headers, body, etc.).
 * @param {object} [config={}] - Additional config.
 * @param {boolean} [config.showErrorToast=true] - Show toast on error.
 * @param {boolean} [config.includeCredentials=true] - Include cookies.
 * @param {string} [config.errorPrefix=''] - Prefix for error messages.
 * @returns {Promise<{ok: boolean, status: number, data: any, error: string|null}>}
 */
export async function apiFetch(url, options = {}, config = {}) {
    const {
        showErrorToast = true,
        includeCredentials = true,
        errorPrefix = '',
    } = config;

    // Set defaults
    options.credentials = includeCredentials ? 'same-origin' : (options.credentials || 'omit');

    // Auto-set Content-Type for JSON bodies
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        options.body = JSON.stringify(options.body);
        options.headers = options.headers || {};
        if (!(options.headers instanceof Headers)) {
            options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/json';
        }
    }

    // CSRF token is auto-injected by the base.html interceptor,
    // but we include it here as a belt-and-suspenders measure
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        options.headers = options.headers || {};
        if (!(options.headers instanceof Headers)) {
            if (!options.headers['X-CSRFToken']) {
                options.headers['X-CSRFToken'] = getCsrfToken();
            }
        }
    }

    try {
        const response = await fetch(url, options);

        // Try to parse JSON response
        let data = null;
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            try {
                data = await response.json();
            } catch (parseError) {
                console.error('Failed to parse JSON response:', parseError);
            }
        } else {
            // For non-JSON responses, get text
            data = await response.text();
        }

        if (!response.ok) {
            const errorMsg = (data && typeof data === 'object' && data.error)
                ? data.error
                : (data && typeof data === 'object' && data.message)
                    ? data.message
                    : `Request failed (${response.status})`;

            const fullError = errorPrefix ? `${errorPrefix}: ${errorMsg}` : errorMsg;

            if (showErrorToast && typeof window.showToast === 'function') {
                window.showToast(fullError, 'danger');
            }

            return { ok: false, status: response.status, data, error: fullError };
        }

        return { ok: true, status: response.status, data, error: null };

    } catch (networkError) {
        const errorMsg = errorPrefix
            ? `${errorPrefix}: Network error`
            : 'Network error — please check your connection';

        if (showErrorToast && typeof window.showToast === 'function') {
            window.showToast(errorMsg, 'danger');
        }

        return { ok: false, status: 0, data: null, error: errorMsg };
    }
}

/**
 * Convenience wrapper for GET requests.
 * @param {string} url
 * @param {object} [config] - Config options (showErrorToast, errorPrefix).
 * @returns {Promise<{ok, status, data, error}>}
 */
export async function apiGet(url, config = {}) {
    return apiFetch(url, { method: 'GET' }, config);
}

/**
 * Convenience wrapper for POST requests.
 * @param {string} url
 * @param {object|FormData} body - Request body (auto-JSON-stringified if object).
 * @param {object} [config] - Config options.
 * @returns {Promise<{ok, status, data, error}>}
 */
export async function apiPost(url, body = null, config = {}) {
    const options = { method: 'POST' };
    if (body !== null) options.body = body;
    return apiFetch(url, options, config);
}

/**
 * Convenience wrapper for PUT requests.
 * @param {string} url
 * @param {object} body
 * @param {object} [config]
 * @returns {Promise<{ok, status, data, error}>}
 */
export async function apiPut(url, body = null, config = {}) {
    const options = { method: 'PUT' };
    if (body !== null) options.body = body;
    return apiFetch(url, options, config);
}

/**
 * Convenience wrapper for DELETE requests.
 * @param {string} url
 * @param {object} [config]
 * @returns {Promise<{ok, status, data, error}>}
 */
export async function apiDelete(url, config = {}) {
    return apiFetch(url, { method: 'DELETE' }, config);
}

/**
 * Convenience wrapper for PATCH requests.
 * @param {string} url
 * @param {object} body
 * @param {object} [config]
 * @returns {Promise<{ok, status, data, error}>}
 */
export async function apiPatch(url, body = null, config = {}) {
    const options = { method: 'PATCH' };
    if (body !== null) options.body = body;
    return apiFetch(url, options, config);
}
