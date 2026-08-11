import '@testing-library/jest-dom';

if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function () {
        this.open = true;
    };
}
if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = function () {
        this.open = false;
        const event = new Event('close');
        this.dispatchEvent(event);
    };
}

// Add scrollIntoView stub to HTMLElement prototype since jsdom doesn't implement it
if (!HTMLElement.prototype.scrollIntoView) {
    HTMLElement.prototype.scrollIntoView = function() {};
}
