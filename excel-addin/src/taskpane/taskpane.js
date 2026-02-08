/* McLarens TRANSFORMIQ - Taskpane UI */
import "./taskpane.css";

function initUI() {
  const statusEl = document.getElementById("status");
  const promptEl = document.getElementById("prompt");
  const modelEl = document.getElementById("model");
  const runBtn = document.getElementById("run");
  const clearBtn = document.getElementById("clear");
  const settingsBtn = document.getElementById("settings");

  if (!statusEl || !promptEl || !modelEl || !runBtn || !clearBtn || !settingsBtn) {
    return;
  }

  const setStatus = (msg) => {
    statusEl.textContent = msg;
  };

  runBtn.addEventListener("click", () => {
    const text = promptEl.value.trim();
    if (!text) {
      setStatus("Type a request first.");
      return;
    }
    setStatus(`Running with ${modelEl.value}...`);
    setTimeout(() => setStatus("Done. Hook your real actions here."), 800);
  });

  clearBtn.addEventListener("click", () => {
    promptEl.value = "";
    setStatus("Cleared.");
  });

  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      setStatus(`Action: ${action} (Model: ${modelEl.value})`);
    });
  });

  settingsBtn.addEventListener("click", () => {
    setStatus("Settings panel: add keys, model, output table, rules.");
  });
}

if (window.Office && Office.onReady) {
  Office.onReady(() => initUI());
} else {
  document.addEventListener("DOMContentLoaded", initUI);
}
