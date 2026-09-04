/**
 * Garmin Connector GUI - Frontend Application Logic
 */

let state = {
  deviceConnected: false,
  deviceModel: null,
  currentFile: null,
  currentContent: null,
  currentParsed: null,
  map: null,
  routeLayer: null,
  markersLayer: null,
  hoverMarker: null,
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initEventListeners();
  checkDeviceStatus();
  fetchCourses();
  initWatcherState();

  // Periodic polling for device and watcher
  setInterval(checkDeviceStatus, 3000);
  setInterval(pollWatcherStatus, 2000);
});

// --- Map Initialization ---
function initMap() {
  const mapElement = document.getElementById("map");
  // Default centered in Europe
  state.map = L.map(mapElement, {
    zoomControl: true,
    attributionControl: false,
  }).setView([46.8182, 8.2275], 6);

  // CartoDB Dark Matter tile layer for dark theme
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    subdomains: "abcd",
  }).addTo(state.map);

  state.markersLayer = L.layerGroup().addTo(state.map);
}

// --- Event Listeners ---
function initEventListeners() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const btnRescan = document.getElementById("btnRescan");
  const btnClearFile = document.getElementById("btnClearFile");
  const btnSideload = document.getElementById("btnSideload");
  const btnDownloadFit = document.getElementById("btnDownloadFit");
  const btnRefreshCourses = document.getElementById("btnRefreshCourses");
  const btnFitMap = document.getElementById("btnFitMap");
  const toggleWatcher = document.getElementById("toggleWatcher");
  const watchPathInput = document.getElementById("watchPath");
  const elevationCanvas = document.getElementById("elevationCanvas");

  // Dropzone drag & drop
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileSelected(files[0]);
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFileSelected(e.target.files[0]);
  });

  btnRescan.addEventListener("click", () => {
    checkDeviceStatus(true);
    fetchCourses();
  });

  btnClearFile.addEventListener("click", resetRouteForm);

  btnFitMap.addEventListener("click", () => {
    if (state.routeLayer && state.map) {
      state.map.fitBounds(state.routeLayer.getBounds(), { padding: [30, 30] });
    }
  });

  btnSideload.addEventListener("click", handleSideload);
  btnDownloadFit.addEventListener("click", handleDownloadFit);
  btnRefreshCourses.addEventListener("click", fetchCourses);

  // Watcher toggle
  toggleWatcher.addEventListener("change", (e) => {
    if (e.target.checked) {
      startWatcher();
    } else {
      stopWatcher();
    }
  });

  // Elevation Hover Interaction
  elevationCanvas.addEventListener("mousemove", handleElevationHover);
  elevationCanvas.addEventListener("mouseleave", () => {
    document.getElementById("elevationHoverInfo").textContent = "Hover over profile";
    if (state.hoverMarker && state.map) {
      state.map.removeLayer(state.hoverMarker);
      state.hoverMarker = null;
    }
  });
}

// --- Device Status Polling ---
async function checkDeviceStatus(showToastOnScan = false) {
  try {
    const res = await fetch("/api/device");
    const data = await res.json();
    const pill = document.getElementById("devicePill");
    const text = document.getElementById("deviceStatusText");
    const btnSideload = document.getElementById("btnSideload");

    state.deviceConnected = data.connected;
    state.deviceModel = data.model_name;

    if (data.connected) {
      pill.className = "device-pill connected";
      text.textContent = `● ${data.model_name} Connected`;
      if (btnSideload) btnSideload.disabled = false;
      if (showToastOnScan) showToast(`Detected ${data.model_name}`, "success");
    } else {
      pill.className = "device-pill disconnected";
      text.textContent = "○ Watch Disconnected (USB/MTP)";
      if (btnSideload) btnSideload.disabled = false; // still allow attempt with clear error
      if (showToastOnScan) showToast("No Garmin watch detected", "info");
    }
  } catch (err) {
    console.error("Device status check failed", err);
  }
}

// --- File Handling & Preview ---
async function handleFileSelected(file) {
  const nameLower = file.name.toLowerCase();
  if (!nameLower.endsWith(".gpx") && !nameLower.endsWith(".fit")) {
    showToast("Please select a .gpx or .fit file", "error");
    return;
  }

  state.currentFile = file;
  document.getElementById("loadedFilename").textContent = file.name;

  const reader = new FileReader();
  reader.onload = async (e) => {
    state.currentContent = e.target.result;
    if (nameLower.endsWith(".gpx")) {
      await previewGpxRoute(state.currentContent, file.name);
    } else {
      showLoadedFitView(file.name);
    }
  };

  if (nameLower.endsWith(".gpx")) {
    reader.readAsText(file);
  } else {
    reader.readAsArrayBuffer(file);
  }
}

async function previewGpxRoute(gpxXml, originalFilename) {
  const sport = document.querySelector('input[name="sport"]:checked')?.value || "cycling";
  const nameInput = document.getElementById("courseName");

  try {
    const res = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gpx_content: gpxXml,
        sport: sport,
        name: nameInput.value.trim() || undefined,
      }),
    });

    const data = await res.json();
    if (!data.success) {
      showToast(data.error || "Failed to preview route", "error");
      return;
    }

    state.currentParsed = data;

    // Show Details Form
    document.getElementById("dropzone").classList.add("hidden");
    document.getElementById("routeDetails").classList.remove("hidden");

    // Fill form
    nameInput.value = data.name;
    document.getElementById("statDistance").textContent = `${(data.total_distance / 1000).toFixed(1)} km`;
    document.getElementById("statAscent").textContent = `${Math.round(data.total_ascent)} m`;
    document.getElementById("statDescent").textContent = `${Math.round(data.total_descent)} m`;
    document.getElementById("statPoints").textContent = data.points_count.toLocaleString();

    // Render Map & Elevation
    renderRouteOnMap(data.coordinates, data.course_points);
    drawElevationProfile(data.elevations);

    showToast(`Loaded ${data.name} (${(data.total_distance / 1000).toFixed(1)} km)`, "info");
  } catch (err) {
    showToast(`Error loading preview: ${err.message}`, "error");
  }
}

function showLoadedFitView(filename) {
  document.getElementById("dropzone").classList.add("hidden");
  document.getElementById("routeDetails").classList.remove("hidden");
  document.getElementById("courseName").value = filename.replace(/\.fit$/i, "").slice(0, 15);
  document.getElementById("statDistance").textContent = "FIT Binary";
  document.getElementById("statAscent").textContent = "--";
  document.getElementById("statDescent").textContent = "--";
  document.getElementById("statPoints").textContent = "Native FIT";
  showToast(`Loaded FIT file '${filename}'`, "info");
}

function resetRouteForm() {
  state.currentFile = null;
  state.currentContent = null;
  state.currentParsed = null;

  document.getElementById("fileInput").value = "";
  document.getElementById("routeDetails").classList.add("hidden");
  document.getElementById("dropzone").classList.remove("hidden");

  if (state.routeLayer && state.map) {
    state.map.removeLayer(state.routeLayer);
    state.routeLayer = null;
  }
  if (state.markersLayer) {
    state.markersLayer.clearLayers();
  }

  clearElevationCanvas();
}

// --- Map Rendering ---
function renderRouteOnMap(coordinates, coursePoints) {
  if (!state.map || !coordinates || coordinates.length === 0) return;

  // Clear existing
  if (state.routeLayer) state.map.removeLayer(state.routeLayer);
  if (state.markersLayer) state.markersLayer.clearLayers();

  // Glow polyline
  state.routeLayer = L.polyline(coordinates, {
    color: "#38bdf8",
    weight: 4,
    opacity: 0.9,
    lineJoin: "round",
  }).addTo(state.map);

  // Start Marker (Green circle)
  const startPt = coordinates[0];
  L.circleMarker(startPt, {
    radius: 7,
    fillColor: "#10b981",
    color: "#ffffff",
    weight: 2,
    fillOpacity: 1,
  }).bindPopup("<b>Start</b>").addTo(state.markersLayer);

  // End Marker (Red circle)
  const endPt = coordinates[coordinates.length - 1];
  L.circleMarker(endPt, {
    radius: 7,
    fillColor: "#ef4444",
    color: "#ffffff",
    weight: 2,
    fillOpacity: 1,
  }).bindPopup("<b>Finish</b>").addTo(state.markersLayer);

  // Course Points (Waypoints / Turn Cues)
  if (coursePoints) {
    coursePoints.forEach((cp) => {
      L.circleMarker([cp.lat, cp.lon], {
        radius: 5,
        fillColor: "#f59e0b",
        color: "#ffffff",
        weight: 1.5,
        fillOpacity: 0.9,
      }).bindPopup(`<b>${cp.name}</b><br>Cue: ${cp.type}<br>Dist: ${cp.dist} km`).addTo(state.markersLayer);
    });
  }

  // Zoom to fit
  state.map.fitBounds(state.routeLayer.getBounds(), { padding: [30, 30] });
}

// --- Elevation Canvas Drawing ---
function drawElevationProfile(elevations) {
  const canvas = document.getElementById("elevationCanvas");
  if (!canvas || !elevations || elevations.length === 0) return;

  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const width = rect.width;
  const height = rect.height;

  ctx.clearRect(0, 0, width, height);

  const validEles = elevations.filter((e) => e.ele !== null).map((e) => e.ele);
  if (validEles.length === 0) return;

  const minEle = Math.min(...validEles);
  const maxEle = Math.max(...validEles);
  const eleRange = Math.max(maxEle - minEle, 10);
  const maxDist = elevations[elevations.length - 1].dist || 1;

  // Background grid line
  ctx.strokeStyle = "rgba(36, 50, 79, 0.4)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height - 10);
  ctx.lineTo(width, height - 10);
  ctx.stroke();

  // Create gradient
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, "rgba(56, 189, 248, 0.4)");
  gradient.addColorStop(1, "rgba(56, 189, 248, 0.0)");

  // Path
  ctx.beginPath();
  ctx.moveTo(0, height);

  elevations.forEach((pt, i) => {
    const x = (pt.dist / maxDist) * width;
    const eleVal = pt.ele !== null ? pt.ele : minEle;
    const y = height - 10 - ((eleVal - minEle) / eleRange) * (height - 25);

    if (i === 0) ctx.lineTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.lineTo(width, height);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Line stroke
  ctx.beginPath();
  elevations.forEach((pt, i) => {
    const x = (pt.dist / maxDist) * width;
    const eleVal = pt.ele !== null ? pt.ele : minEle;
    const y = height - 10 - ((eleVal - minEle) / eleRange) * (height - 25);

    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 2;
  ctx.stroke();
}

function clearElevationCanvas() {
  const canvas = document.getElementById("elevationCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function handleElevationHover(e) {
  if (!state.currentParsed || !state.currentParsed.elevations) return;

  const canvas = document.getElementById("elevationCanvas");
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const ratio = Math.max(0, Math.min(1, mouseX / rect.width));

  const elevations = state.currentParsed.elevations;
  const coords = state.currentParsed.coordinates;
  const index = Math.floor(ratio * (elevations.length - 1));
  const currentPt = elevations[index];

  if (currentPt) {
    document.getElementById("elevationHoverInfo").textContent = `${currentPt.dist} km | ${currentPt.ele !== null ? Math.round(currentPt.ele) + 'm' : '--'}`;

    if (coords && coords[index] && state.map) {
      const latLng = coords[index];
      if (!state.hoverMarker) {
        state.hoverMarker = L.circleMarker(latLng, {
          radius: 6,
          fillColor: "#38bdf8",
          color: "#ffffff",
          weight: 2,
          fillOpacity: 1,
        }).addTo(state.map);
      } else {
        state.hoverMarker.setLatLng(latLng);
      }
    }
  }
}

// --- Sideload & Download ---
async function handleSideload() {
  if (!state.currentFile) {
    showToast("Please select a route file first", "error");
    return;
  }

  const btnSideload = document.getElementById("btnSideload");
  btnSideload.disabled = true;
  btnSideload.textContent = "Sideloading...";

  const sport = document.querySelector('input[name="sport"]:checked')?.value || "cycling";
  const courseName = document.getElementById("courseName").value.trim();

  try {
    let payloadContent = state.currentContent;
    if (state.currentFile.name.toLowerCase().endsWith(".fit")) {
      // base64 encode ArrayBuffer
      const bytes = new Uint8Array(state.currentContent);
      let binary = "";
      for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
      payloadContent = btoa(binary);
    }

    const res = await fetch("/api/sideload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: state.currentFile.name,
        content: payloadContent,
        sport: sport,
        name: courseName || undefined,
      }),
    });

    const data = await res.json();
    if (data.success) {
      showToast(data.message || "Successfully sideloaded to watch!", "success");
      fetchCourses();
    } else {
      showToast(data.error || "Sideload failed", "error");
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btnSideload.disabled = false;
    btnSideload.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Sideload to Watch`;
  }
}

async function handleDownloadFit() {
  if (!state.currentFile) return;

  if (state.currentFile.name.toLowerCase().endsWith(".fit")) {
    const blob = new Blob([state.currentContent], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = state.currentFile.name;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Downloaded FIT file", "success");
    return;
  }

  // Trigger preview -> binary generation on server
  showToast("Preparing FIT course download...", "info");
  try {
    const courseName = document.getElementById("courseName").value.trim() || state.currentFile.name.replace(/\.gpx$/i, "");
    const sport = document.querySelector('input[name="sport"]:checked')?.value || "cycling";

    const res = await fetch("/api/sideload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: state.currentFile.name,
        content: state.currentContent,
        sport: sport,
        name: courseName,
      }),
    });
    const data = await res.json();
    if (data.success) {
      showToast("Course compiled successfully!", "success");
    }
  } catch (err) {
    showToast(`Conversion error: ${err.message}`, "error");
  }
}

// --- Courses List ---
async function fetchCourses() {
  try {
    const res = await fetch("/api/courses");
    const data = await res.json();
    const tbody = document.getElementById("coursesTableBody");

    if (!data.connected || !data.courses || data.courses.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="empty-state">${data.connected ? 'No courses currently stored on watch.' : 'No Garmin watch connected via USB/MTP.'}</td></tr>`;
      return;
    }

    tbody.innerHTML = data.courses
      .map((c) => {
        const sizeKb = (c.size_bytes / 1024).toFixed(1) + " KB";
        const isStaged = c.location.includes("Pending");
        const statusBadge = isStaged
          ? `<span class="badge" style="background:rgba(245,158,11,0.2);color:#fbbf24;border-color:rgba(245,158,11,0.4)">Pending Ingest</span>`
          : `<span class="badge" style="background:rgba(16,185,129,0.2);color:#34d399;border-color:rgba(16,185,129,0.4)">Installed</span>`;

        return `
          <tr>
            <td class="course-name">${escapeHtml(c.filename)}</td>
            <td>${statusBadge}</td>
            <td>${sizeKb}</td>
            <td>
              <button class="btn btn-danger btn-small" onclick="deleteCourse('${escapeHtml(c.filename)}')">Delete</button>
            </td>
          </tr>
        `;
      })
      .join("");
  } catch (err) {
    console.error("Failed to fetch courses", err);
  }
}

async function deleteCourse(filename) {
  if (!confirm(`Delete '${filename}' from Garmin watch?`)) return;

  try {
    const res = await fetch(`/api/courses/${encodeURIComponent(filename)}`, { method: "DELETE" });
    const data = await res.json();
    if (data.success) {
      showToast(`Deleted '${filename}'`, "success");
      fetchCourses();
    } else {
      showToast(data.error || "Failed to delete course", "error");
    }
  } catch (err) {
    showToast(`Error deleting course: ${err.message}`, "error");
  }
}

// --- Watcher Management ---
async function initWatcherState() {
  try {
    const res = await fetch("/api/watcher/status");
    const data = await res.json();
    document.getElementById("toggleWatcher").checked = data.is_running;
    if (data.watch_path) document.getElementById("watchPath").value = data.watch_path;
    updateWatcherLogs(data.logs);
  } catch (err) {}
}

async function startWatcher() {
  const path = document.getElementById("watchPath").value.trim();
  const sport = document.querySelector('input[name="sport"]:checked')?.value || "cycling";

  try {
    const res = await fetch("/api/watcher/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path, sport: sport }),
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Started monitoring '${data.watch_path}'`, "success");
    }
  } catch (err) {
    showToast(`Failed to start watcher: ${err.message}`, "error");
  }
}

async function stopWatcher() {
  try {
    const res = await fetch("/api/watcher/stop", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      showToast("Stopped folder monitoring", "info");
    }
  } catch (err) {
    showToast(`Error stopping watcher: ${err.message}`, "error");
  }
}

async function pollWatcherStatus() {
  try {
    const res = await fetch("/api/watcher/status");
    const data = await res.json();
    updateWatcherLogs(data.logs);
  } catch (err) {}
}

function updateWatcherLogs(logs) {
  if (!logs || logs.length === 0) return;
  const container = document.getElementById("watcherLogs");
  container.innerHTML = logs.map((l) => `<div class="log-entry">${escapeHtml(l)}</div>`).join("");
  container.scrollTop = container.scrollHeight;
}

// --- Toasts & Helpers ---
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const icon =
    type === "success"
      ? "✔"
      : type === "error"
      ? "✖"
      : "ℹ";

  toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
