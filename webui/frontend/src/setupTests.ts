import '@testing-library/jest-dom';

// Mock scrollIntoView which is not implemented in jsdom
window.HTMLElement.prototype.scrollIntoView = function() {};

window.HTMLDialogElement.prototype.showModal = function() {
  this.open = true;
};
window.HTMLDialogElement.prototype.close = function() {
  this.open = false;
};
