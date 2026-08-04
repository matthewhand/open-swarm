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
