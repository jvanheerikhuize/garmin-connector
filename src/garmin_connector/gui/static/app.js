"use strict";

const POLL_INTERVAL_MS = 3000;
const MISSING_CYCLE_THRESHOLD = 7;

let lastKnownState = "disconnected";
let missingCycles = 0;

function enableMap() {}
function disableAndResetMap() {}
function fetchCourses() {}
function courseListIsEmpty() {
  return true;
}

function setConnected(modelName) {
  missingCycles = 0;
  lastKnownState = "connected";
  document.getElementById("statusDot").className = "status-dot connected";
  document.getElementById("deviceStatus").textContent = "Connected: " + (modelName || "Garmin Watch");
  enableMap();
  if (courseListIsEmpty()) {
    fetchCourses();
  }
}

function setDisconnected() {
  missingCycles += 1;
  if (missingCycles < MISSING_CYCLE_THRESHOLD) {
    return;
  }
  lastKnownState = "disconnected";
  document.getElementById("statusDot").className = "status-dot disconnected";
  document.getElementById("deviceStatus").textContent = "No watch connected";
  disableAndResetMap();
}

async function checkDeviceStatus() {
  try {
    const response = await fetch("/api/device");
    const data = await response.json();
    if (data && data.connected) {
      setConnected(data.model_name);
    } else {
      setDisconnected();
    }
  } catch (err) {
    console.error("Device status poll failed:", err);
    setDisconnected();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkDeviceStatus();
  setInterval(checkDeviceStatus, POLL_INTERVAL_MS);
});
