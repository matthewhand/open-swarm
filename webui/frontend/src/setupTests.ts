import '@testing-library/jest-dom';
import { resetChatConnection } from './lib/chatConnection';
import { resetExpectedSpaVersion } from './lib/spaHello';
import { resetGithubReleaseCache } from './lib/githubRelease';
import { setBakedSpaVersionForTests } from './lib/spaVersion';

afterEach(() => {
    resetChatConnection();
    resetExpectedSpaVersion();
    resetGithubReleaseCache();
    setBakedSpaVersionForTests(null);
});

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
