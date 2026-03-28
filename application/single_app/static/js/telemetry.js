// telemetry.js
// Frontend error logging and telemetry for Application Insights
// Captures unhandled errors, promise rejections, and custom events

(function () {
    'use strict';

    const ERROR_ENDPOINT = '/api/telemetry/frontend-error';
    const EVENT_ENDPOINT = '/api/telemetry/frontend-event';
    const MAX_ERRORS_PER_MINUTE = 10;

    let errorCount = 0;
    let errorResetTimer = null;

    function resetErrorCount() {
        errorCount = 0;
    }

    function sendError(message, source, stack, url) {
        if (errorCount >= MAX_ERRORS_PER_MINUTE) return;
        errorCount++;

        if (!errorResetTimer) {
            errorResetTimer = setInterval(resetErrorCount, 60000);
        }

        try {
            fetch(ERROR_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    message: String(message).substring(0, 500),
                    source: String(source || 'unknown').substring(0, 200),
                    stack: String(stack || '').substring(0, 1000),
                    url: String(url || window.location.href).substring(0, 500),
                }),
            }).catch(function () { /* swallow fetch errors silently */ });
        } catch (e) {
            // Never throw from error handler
        }
    }

    // Capture unhandled JS errors
    window.addEventListener('error', function (event) {
        sendError(
            event.message || 'Script error',
            event.filename || 'unknown',
            event.error ? event.error.stack : '',
            window.location.href
        );
    });

    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', function (event) {
        var reason = event.reason || {};
        sendError(
            reason.message || String(reason).substring(0, 500),
            'unhandledrejection',
            reason.stack || '',
            window.location.href
        );
    });

    // Public API for custom telemetry events
    window.scTelemetry = {
        logError: function (message, source, extra) {
            sendError(message, source || 'custom', extra || '', window.location.href);
        },

        logEvent: function (eventName, properties) {
            try {
                fetch(EVENT_ENDPOINT, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        event: String(eventName).substring(0, 100),
                        properties: properties || {},
                    }),
                }).catch(function () { /* swallow */ });
            } catch (e) {
                // Never throw from event logger
            }
        },

        // Track user actions (click events, navigation, feature usage)
        trackAction: function (action, category, label) {
            this.logEvent('user_action', {
                action: action,
                category: category || 'general',
                label: label || '',
                page: window.location.pathname,
            });
        },

        // Track page views
        trackPageView: function () {
            this.logEvent('page_view', {
                page: window.location.pathname,
                referrer: document.referrer || '',
                title: document.title,
            });
        },

        // Track feature usage
        trackFeature: function (featureName, details) {
            this.logEvent('feature_used', {
                feature: featureName,
                details: details || '',
                page: window.location.pathname,
            });
        },

        // Track timing (e.g., API call duration)
        trackTiming: function (name, durationMs) {
            this.logEvent('timing', {
                name: name,
                duration_ms: durationMs,
                page: window.location.pathname,
            });
        },
    };

    // Auto-track page views
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            window.scTelemetry.trackPageView();
        });
    } else {
        window.scTelemetry.trackPageView();
    }
})();
