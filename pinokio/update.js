// Pinokio update — pull this sideload clone, then reuse install.js (compose build).
// Exists so the Start+Update menu does not point at a missing file.

module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: "git pull --ff-only",
      },
    },
    {
      method: "script.start",
      params: {
        uri: "pinokio/install.js",
      },
    },
  ],
}
