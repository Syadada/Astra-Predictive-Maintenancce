/**
 * PredictaGuard API client — shared fetch helper for all dashboard pages.
 * Works only when the page is served via http://localhost:8000 (FastAPI).
 * Pages opened via file:// will skip API calls gracefully.
 */

const PG_API_BASE = '';   // same origin — FastAPI serves dashboard + API

/** Returns true when running via HTTP (not file://). */
function pgApiAvailable() {
    return window.location.protocol === 'http:' || window.location.protocol === 'https:';
}

/**
 * Generic API call. Returns parsed JSON or throws on error.
 * @param {string} path  e.g. '/api/equipment/status'
 * @param {RequestInit} [options]
 */
async function pgFetch(path, options = {}) {
    const res = await fetch(PG_API_BASE + path, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
    return res.json();
}

/**
 * Start a polling loop. Calls callback() immediately, then every intervalMs.
 * Returns the interval ID so it can be cleared.
 */
function pgStartPolling(callback, intervalMs = 5000) {
    callback();
    return setInterval(callback, intervalMs);
}

/** Advance the simulator cursor by one step (call on each poll). */
async function pgSimStep() {
    try { await pgFetch('/api/simulate/step'); } catch (_) { /* silent */ }
}
