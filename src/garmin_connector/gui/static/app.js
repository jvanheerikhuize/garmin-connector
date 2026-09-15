"use strict";

// ---------------------------------------------------------------------------
// Connection status shell (spec: connection-status-shell)
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 3000;
const MISSING_CYCLE_THRESHOLD = 7;

let lastKnownState = "disconnected";
let missingCycles = 0;

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

// ---------------------------------------------------------------------------
// Course management & map preview (spec: gui-course-frontend)
// ---------------------------------------------------------------------------

const MAP_DEFAULT_CENTER = [51.505, -0.09];
const MAP_DEFAULT_ZOOM = 4;
const TRACK_COLOR = "#00f0ff";
const TOAST_LIFETIME_MS = 4500;
const TOAST_ANIMATION = "0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards";

let map = null;
let trackLayer = null;
let selectedSport = "cycling";
let courseToDelete = null;
let courseCount = 0;

function $(id) {
  return document.getElementById(id);
}

function courseListIsEmpty() {
  return courseCount === 0;
}

function showOverlay(text) {
  const overlay = $("mapEmptyOverlay");
  overlay.querySelector(".empty-overlay-content").textContent = text;
  overlay.style.display = "flex";
}

function hideOverlay() {
  $("mapEmptyOverlay").style.display = "none";
}

function setMapInfo(text) {
  $("mapInfo").textContent = text;
}

function setInteraction(enabled) {
  const handlers = [map.dragging, map.touchZoom, map.doubleClickZoom, map.scrollWheelZoom, map.boxZoom, map.keyboard];
  handlers.forEach((h) => {
    if (!h) return;
    if (enabled) h.enable();
    else h.disable();
  });
}

function setControlsEnabled(enabled) {
  $("btnOpenIngestModal").disabled = !enabled;
  $("btnRefresh").disabled = !enabled;
  const dropZone = $("dropZone");
  dropZone.style.pointerEvents = enabled ? "" : "none";
  dropZone.style.opacity = enabled ? "" : "0.4";
}

function clearTrack() {
  if (trackLayer) {
    map.removeLayer(trackLayer);
    trackLayer = null;
  }
}

function initMap() {
  map = L.map("map", { zoomControl: true, attributionControl: true }).setView(MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
  }).addTo(map);
}

function disableAndResetMap() {
  clearTrack();
  map.setView(MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM);
  setInteraction(false);
  document.querySelector(".map-viewport-container").classList.add("map-disabled");
  showOverlay("Connect watch via USB to enable route preview");
  setMapInfo("No watch connected");
  setControlsEnabled(false);
}

function enableMap() {
  setInteraction(true);
  document.querySelector(".map-viewport-container").classList.remove("map-disabled");
  setControlsEnabled(true);
  if (!trackLayer) {
    showOverlay("Select a course to preview route");
    if ($("mapInfo").textContent === "No watch connected") {
      setMapInfo("No route selected");
    }
  } else {
    hideOverlay();
  }
}

function resetMapToNoRoute() {
  clearTrack();
  showOverlay("Select a course to preview route");
  setMapInfo("No route selected");
}

async function mapCourse(filename) {
  setMapInfo("Loading route: " + filename + "...");
  try {
    const response = await fetch("/api/fetch-course/" + encodeURIComponent(filename));
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || "Unknown error");
    }
    clearTrack();
    if (data.points && data.points.length > 0) {
      trackLayer = L.polyline(data.points, {
        color: TRACK_COLOR,
        weight: 4,
        opacity: 0.9,
        className: "glowing-track",
      }).addTo(map);
      map.fitBounds(trackLayer.getBounds(), { padding: [30, 30] });
      hideOverlay();
      setMapInfo("Showing: " + filename + " (" + data.points.length + " trackpoints)");
    } else {
      const msg = "No GPS trackpoints found in " + filename;
      showOverlay(msg);
      setMapInfo(msg);
    }
  } catch (err) {
    const msg = "Failed to load route: " + err.message;
    showOverlay(msg);
    setMapInfo(msg);
    showMessage(msg, "error");
  }
}

function formatKb(bytes) {
  return Math.round(bytes / 1024) + " KB";
}

function renderCourses(courses) {
  const container = $("courseTableBody");
  container.innerHTML = "";
  courses.forEach((course) => {
    const isFit = course.filename.toLowerCase().endsWith(".fit");
    const row = document.createElement("div");
    row.className = "course-row";

    const left = document.createElement("div");
    left.className = "course-row-left";

    const badge = document.createElement("span");
    badge.className = "course-format-badge " + (isFit ? "course-format-fit" : "course-format-gpx");
    badge.textContent = isFit ? "FIT" : "GPX";

    const details = document.createElement("div");
    details.className = "course-details";
    const pathEl = document.createElement("div");
    pathEl.className = "course-path";
    pathEl.textContent = course.watch_path || "/GARMIN/Courses/" + course.filename;
    pathEl.title = course.full_path || "";
    const meta = document.createElement("div");
    meta.className = "course-meta";
    meta.textContent = formatKb(course.size_bytes);
    details.appendChild(pathEl);
    details.appendChild(meta);

    left.appendChild(badge);
    left.appendChild(details);

    const actions = document.createElement("div");
    actions.className = "course-actions";
    const mapBtn = document.createElement("button");
    mapBtn.className = "btn btn-sm btn-primary";
    mapBtn.textContent = "Map";
    mapBtn.addEventListener("click", () => mapCourse(course.filename));
    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-sm btn-danger";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => openConfirmModal(course.filename));
    actions.appendChild(mapBtn);
    actions.appendChild(delBtn);

    row.appendChild(left);
    row.appendChild(actions);
    container.appendChild(row);
  });
}

function renderEmptyCourses(text) {
  const container = $("courseTableBody");
  container.innerHTML = "";
  const empty = document.createElement("div");
  empty.className = "empty-courses";
  empty.textContent = text;
  container.appendChild(empty);
}

function updateStatusWithCounts(courses) {
  const statusEl = $("deviceStatus");
  if (!statusEl.textContent.startsWith("Connected")) {
    return;
  }
  const base = statusEl.textContent.replace(/\s*\(.*\)$/, "");
  if (courses.length === 0) {
    statusEl.textContent = base + " (0 courses)";
    return;
  }
  let pending = 0;
  let synced = 0;
  courses.forEach((c) => {
    const loc = (c.location || "").toUpperCase();
    if (loc.includes("NEWFILES")) pending += 1;
    else if (loc.includes("COURSES")) synced += 1;
  });
  let summary = courses.length + " courses";
  if (pending > 0) summary += ", " + pending + " pending sync";
  statusEl.textContent = base + " (" + summary + ")";
}

async function fetchCourses() {
  try {
    const response = await fetch("/api/courses");
    const data = await response.json();
    const courses = (data && data.courses) || [];
    courseCount = courses.length;
    if (courses.length === 0) {
      renderEmptyCourses("No courses found in watch storage");
    } else {
      renderCourses(courses);
    }
    updateStatusWithCounts(courses);
  } catch (err) {
    console.error("Failed to fetch courses:", err);
  }
}

// --- Ingest flow -----------------------------------------------------------

function openIngestModal() {
  $("ingestModal").classList.add("cyber-modal--open");
}

function closeIngestModal() {
  $("ingestModal").classList.remove("cyber-modal--open");
}

function selectSport(sport) {
  selectedSport = sport;
  document.querySelectorAll(".sport-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.sport === sport);
  });
}

function handleFileUpload(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".gpx")) {
    showMessage("Only .gpx files are supported: " + file.name, "error");
    return;
  }
  showMessage("Ingesting " + file.name + " for " + selectedSport + "...", "warning");
  const reader = new FileReader();
  reader.onload = async () => {
    try {
      const response = await fetch("/api/sideload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gpx_content: reader.result,
          course_name: file.name.replace(/\.gpx$/i, ""),
          sport: selectedSport,
        }),
      });
      const data = await response.json();
      if (data.success) {
        showMessage("Successfully converted & sideloaded: " + data.filename, "success");
        setTimeout(closeIngestModal, 500);
        fetchCourses();
        checkDeviceStatus();
      } else {
        showMessage(data.error || "Sideload failed", "error");
      }
    } catch (err) {
      showMessage("Network error: " + err.message, "error");
    }
  };
  reader.readAsText(file);
}

// --- Deletion flow ---------------------------------------------------------

function openConfirmModal(filename) {
  courseToDelete = filename;
  $("confirmModalText").textContent = "Delete " + filename + " from the watch? This cannot be undone.";
  $("confirmModal").classList.add("cyber-modal--open");
}

function closeConfirmModal() {
  courseToDelete = null;
  $("confirmModal").classList.remove("cyber-modal--open");
}

async function confirmDelete() {
  const filename = courseToDelete;
  if (!filename) return;
  closeConfirmModal();
  try {
    const response = await fetch("/api/courses/" + encodeURIComponent(filename), { method: "DELETE" });
    if (response.ok) {
      resetMapToNoRoute();
      fetchCourses();
      checkDeviceStatus();
      showMessage("Deleted " + filename, "success");
    } else {
      showMessage("Failed to delete " + filename, "error");
    }
  } catch (err) {
    showMessage("Delete failed: " + err.message, "error");
  }
}

// --- Toasts ----------------------------------------------------------------

function showMessage(msg, type) {
  const kind = type === "success" || type === "error" ? type : "warning";
  const titles = { success: "Success", error: "Error", warning: "Notice" };
  const toast = document.createElement("div");
  toast.className = "cyber-alert cyber-alert--" + kind + " cyber-toast";
  const title = document.createElement("div");
  title.className = "cyber-alert__title";
  title.textContent = titles[kind];
  const body = document.createElement("div");
  body.style.fontSize = "0.85rem";
  body.style.fontFamily = "var(--font-mono)";
  body.textContent = msg;
  toast.appendChild(title);
  toast.appendChild(body);
  $("toastContainer").appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "toastSlideOut " + TOAST_ANIMATION;
    setTimeout(() => toast.remove(), 300);
  }, TOAST_LIFETIME_MS);
}

// --- Wiring ----------------------------------------------------------------

function bindEvents() {
  $("btnOpenIngestModal").addEventListener("click", openIngestModal);
  $("btnRefresh").addEventListener("click", fetchCourses);
  $("ingestModalClose").addEventListener("click", closeIngestModal);
  $("btnCancelIngest").addEventListener("click", closeIngestModal);
  $("confirmModalClose").addEventListener("click", closeConfirmModal);
  $("btnConfirmCancel").addEventListener("click", closeConfirmModal);
  $("btnConfirmDelete").addEventListener("click", confirmDelete);

  document.querySelectorAll(".sport-btn").forEach((btn) => {
    btn.addEventListener("click", () => selectSport(btn.dataset.sport));
  });

  const dropZone = $("dropZone");
  const fileInput = $("fileInput");
  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    handleFileUpload(fileInput.files[0]);
    fileInput.value = "";
  });
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    handleFileUpload(e.dataTransfer.files[0]);
  });

  [$("ingestModal"), $("confirmModal")].forEach((modal) => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        if (modal.id === "ingestModal") closeIngestModal();
        else closeConfirmModal();
      }
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeIngestModal();
      closeConfirmModal();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  bindEvents();
  disableAndResetMap();
  checkDeviceStatus();
  setInterval(checkDeviceStatus, POLL_INTERVAL_MS);
});
