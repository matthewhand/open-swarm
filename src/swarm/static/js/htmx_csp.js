// Keep HTMX from injecting a <style> tag (breaks style-src 'self' CSP).
// Indicator rules live in static/css/operator.css instead.
htmx.config.includeIndicatorStyles = false;
