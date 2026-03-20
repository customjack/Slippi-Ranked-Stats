import { mount } from "svelte";
import App from "./App.svelte";
import "./styles/global.css";

function showError(err: unknown) {
  document.body.style.cssText = "background:#1e1e1e;color:#e74c3c;font-family:monospace;padding:24px;white-space:pre-wrap";
  document.body.textContent = "App failed to start:\n\n" + String(err);
}

window.addEventListener("unhandledrejection", (e) => showError(e.reason));
window.addEventListener("error", (e) => showError(e.error ?? e.message));

try {
  mount(App, { target: document.getElementById("app")! });
} catch (err) {
  showError(err);
}
