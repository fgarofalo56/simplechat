// dom-helpers.js
// DOM manipulation utilities for XSS-safe content rendering.
// Use these instead of raw innerHTML with untrusted data.
//
// Usage:
//   import { escapeHtml, safeText, createEl } from '/static/js/utils/dom-helpers.js';
//
//   element.textContent = escapeHtml(userInput);
//   const el = createEl('span', { class: 'badge' }, [escapeHtml(tag)]);

/**
 * Escape HTML special characters to prevent XSS.
 * Use this when inserting untrusted strings into HTML context.
 *
 * @param {string} str - The string to escape.
 * @returns {string} HTML-entity-encoded string.
 */
export function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const s = String(str);
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return s.replace(/[&<>"']/g, ch => map[ch]);
}

/**
 * Safely set text content on an element.
 * Uses textContent (not innerHTML) to prevent XSS.
 *
 * @param {HTMLElement} element - Target DOM element.
 * @param {string} text - Text to set.
 */
export function safeText(element, text) {
    if (element) {
        element.textContent = text || '';
    }
}

/**
 * Create a DOM element with attributes and children.
 * Safer alternative to innerHTML for building DOM programmatically.
 *
 * @param {string} tag - HTML tag name (e.g., 'div', 'span', 'button').
 * @param {object} [attrs={}] - Attributes to set (class, id, data-*, aria-*, etc.).
 * @param {Array<string|HTMLElement>} [children=[]] - Child nodes.
 *   Strings are added as text nodes (safe from XSS).
 *   HTMLElements are appended as-is.
 * @returns {HTMLElement} The created element.
 *
 * @example
 *   const btn = createEl('button', {
 *     class: 'btn btn-primary',
 *     'aria-label': 'Save document',
 *     onclick: () => save(),
 *   }, ['Save']);
 */
export function createEl(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);

    for (const [key, value] of Object.entries(attrs)) {
        if (key === 'class' || key === 'className') {
            el.className = value;
        } else if (key.startsWith('on') && typeof value === 'function') {
            // Event handlers: onclick, onchange, etc.
            el.addEventListener(key.slice(2).toLowerCase(), value);
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(el.style, value);
        } else if (key === 'dataset' && typeof value === 'object') {
            for (const [dk, dv] of Object.entries(value)) {
                el.dataset[dk] = dv;
            }
        } else if (value === true) {
            el.setAttribute(key, '');
        } else if (value !== false && value !== null && value !== undefined) {
            el.setAttribute(key, String(value));
        }
    }

    for (const child of children) {
        if (typeof child === 'string') {
            el.appendChild(document.createTextNode(child));
        } else if (child instanceof Node) {
            el.appendChild(child);
        }
    }

    return el;
}

/**
 * Sanitize a string for safe use as an HTML attribute value.
 * More aggressive than escapeHtml — also handles backticks and equals.
 *
 * @param {string} str - The string to sanitize.
 * @returns {string} Safe attribute value.
 */
export function sanitizeAttr(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/`/g, '&#96;');
}

/**
 * Build an HTML string from a template with auto-escaped values.
 * Use for cases where innerHTML is unavoidable (e.g., markdown rendering).
 *
 * @param {string[]} strings - Template literal strings.
 * @param {...any} values - Template literal values (auto-escaped).
 * @returns {string} HTML string with escaped interpolations.
 *
 * @example
 *   element.innerHTML = safeHTML`<span class="name">${userName}</span>`;
 */
export function safeHTML(strings, ...values) {
    let result = '';
    for (let i = 0; i < strings.length; i++) {
        result += strings[i];
        if (i < values.length) {
            result += escapeHtml(values[i]);
        }
    }
    return result;
}
