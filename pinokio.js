// Open Swarm — Pinokio launcher (local sideload only).
// Sideload via git URL. No public Discover listing from this tree.
//
// Menu shape follows matthewhand/gpt-terminal-plus (Install / Start+Update /
// Open App) but this repo ships the root install.js + start.js that repo
// pointed at and was missing.

const path = require("path")

const INSTALLED_MARK = path.join(".pinokio", "installed")

function isPromise(value) {
  return !!value && typeof value.then === "function"
}

async function exists(info, kernel, rel) {
  if (info && typeof info.exists === "function") {
    return !!info.exists(rel)
  }
  if (kernel && typeof kernel.exists === "function") {
    // Current Pinokio: info.exists(rel). Older kernels: exists(cwd, rel).
    let result = kernel.exists(rel)
    if (isPromise(result)) result = await result
    if (result) return true
    if (typeof __dirname === "string") {
      result = kernel.exists(__dirname, rel)
      if (isPromise(result)) result = await result
      return !!result
    }
  }
  return false
}

function running(info, kernel, rel) {
  if (info && typeof info.running === "function") {
    return !!info.running(rel)
  }
  if (kernel && typeof kernel.running === "function") {
    if (kernel.running(rel)) return true
    if (typeof __dirname === "string" && kernel.running(__dirname, rel)) return true
  }
  return false
}

async function menu(kernel, info) {
  const installed = await exists(info, kernel, INSTALLED_MARK)
  const installing = running(info, kernel, "install.js")
  const starting = running(info, kernel, "start.js")
  const updating = running(info, kernel, "update.js")

  if (installing) {
    return [{
      default: true,
      icon: "fa-solid fa-plug",
      text: "Installing",
      href: "install.js",
    }]
  }

  if (updating) {
    return [{
      default: true,
      icon: "fa-solid fa-clock",
      text: "Updating",
      href: "update.js",
    }]
  }

  if (starting) {
    // REQ-47: running → Open App (href start.js, default)
    return [{
      default: true,
      icon: "fa-solid fa-rocket",
      text: "Open App",
      href: "start.js",
    }]
  }

  if (installed) {
    // installed + stopped → Start + Update
    return [{
      default: true,
      icon: "fa-solid fa-power-off",
      text: "Start",
      href: "start.js",
    }, {
      icon: "fa-solid fa-rotate",
      text: "Update",
      href: "update.js",
    }]
  }

  // not installed → Install
  return [{
    default: true,
    icon: "fa-solid fa-plug",
    text: "Install",
    href: "install.js",
  }]
}

module.exports = {
  version: "2.0",
  title: "Open Swarm",
  description: "Open Swarm — multi-agent AI workflows as a local CLI, OpenAI-compatible API, and web UI.",
  icon: "assets/brand/favicon-minimal.svg",
  menu,
}
