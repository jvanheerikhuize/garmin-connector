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
  state.map = L.map(mapElement, {
    zoomControl: true,
    attributionControl: true,
  }).setView([46.8182, 8.2275], 6);

  // 100% Free basemaps (No API keys required)
  const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap",
  });

  const topo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 17,
    attribution: "© OpenTopoMap",
  });

  const cyclosm = L.tileLayer("https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© CyclOSM",
  });

  const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: "© Esri Imagery",
  });

  // Default layer
  osm.addTo(state.map);

  // Layer control switcher
  const baseLayers = {
    "🗺️ OpenStreetMap": osm,
    "⛰️ OpenTopoMap": topo,
    "🚴 CyclOSM": cyclosm,
    "🛰️ Satellite": satellite,
  };
  L.control.layers(baseLayers, null, { position: "topright" }).addTo(state.map);

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
  const elevationSvgWrapper = document.querySelector(".elevation-svg-wrapper");

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
  if (elevationSvgWrapper) {
    elevationSvgWrapper.addEventListener("mousemove", handleElevationHover);
    elevationSvgWrapper.addEventListener("mouseleave", () => {
      document.getElementById("elevationHoverInfo").textContent = "Hover profile to inspect";
      const hoverLine = document.getElementById("hoverLine");
      const hoverDot = document.getElementById("hoverDot");
      if (hoverLine) hoverLine.style.display = "none";
      if (hoverDot) hoverDot.style.display = "none";

      if (state.hoverMarker && state.map) {
        state.map.removeLayer(state.hoverMarker);
        state.hoverMarker = null;
      }
    });
  }
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
      pill.title = `Connected at ${data.mount_point || 'GARMIN storage'}`;
      if (btnSideload) btnSideload.disabled = false;
      if (showToastOnScan) showToast(`Detected ${data.model_name}`, "success");
    } else if (data.raw_usb && data.raw_usb.detected) {
      if (data.raw_usb.is_protocol_mode) {
        pill.className = "device-pill warning";
        text.textContent = `◐ Garmin Connected (Garmin Mode)`;
        pill.title = "Watch is connected in Garmin Protocol mode. Tap 'Yes' on the watch screen or set Settings > System > USB Mode to MTP/Storage to enable file transfers.";
        if (showToastOnScan) showToast("Garmin watch connected! Tap 'Yes' on watch screen to unlock storage.", "info");
      } else {
        pill.className = "device-pill warning";
        text.textContent = `◐ Garmin USB Detected (Mounting...)`;
        pill.title = "Device detected on USB bus. Initializing mount...";
      }
    } else {
      pill.className = "device-pill disconnected";
      text.textContent = "○ Watch Disconnected (USB)";
      pill.title = "No Garmin watch detected via USB cable.";
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

// --- Elevation Profile SVG Drawing ---
function drawElevationProfile(elevations) {
  const svg = document.getElementById("elevationSvg");
  if (!svg) return;

  const validEles = (elevations || []).filter((e) => e.ele !== null && !isNaN(e.ele)).map((e) => e.ele);
  if (!elevations || elevations.length < 2 || validEles.length === 0) {
    svg.innerHTML = `
      <defs>
        <linearGradient id="elevationGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.45" />
          <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      <text x="300" y="55" text-anchor="middle" fill="#64748b" font-size="12" font-family="sans-serif">Flat route or no elevation coordinates in file</text>
    `;
    return;
  }

  const width = 600;
  const height = 110;
  const padding = { top: 12, right: 15, bottom: 22, left: 42 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  let minEle = Math.min(...validEles);
  let maxEle = Math.max(...validEles);
  if (maxEle - minEle < 10) {
    minEle = Math.max(0, minEle - 10);
    maxEle = maxEle + 10;
  }
  const eleRange = maxEle - minEle;
  const maxDist = elevations[elevations.length - 1].dist || 1;

  const scaleX = (dist) => (padding.left + (dist / maxDist) * chartW).toFixed(1);
  const scaleY = (ele) => {
    const val = ele !== null && !isNaN(ele) ? ele : minEle;
    return (padding.top + chartH - ((val - minEle) / eleRange) * chartH).toFixed(1);
  };

  const pts = elevations.map((p) => `${scaleX(p.dist)},${scaleY(p.ele)}`);
  const linePath = `M ${pts.join(" L ")}`;
  const areaPath = `${linePath} L ${padding.left + chartW},${(padding.top + chartH).toFixed(1)} L ${padding.left},${(padding.top + chartH).toFixed(1)} Z`;

  svg.innerHTML = `
    <defs>
      <linearGradient id="elevationGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.45" />
        <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.02" />
      </linearGradient>
    </defs>
    <!-- Axis Grid Lines -->
    <line x1="${padding.left}" y1="${padding.top + chartH}" x2="${padding.left + chartW}" y2="${padding.top + chartH}" stroke="#24324f" stroke-width="1" />
    <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${padding.top + chartH}" stroke="#24324f" stroke-width="1" />
    <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left + chartW}" y2="${padding.top}" stroke="rgba(36,50,79,0.4)" stroke-width="1" stroke-dasharray="2 2" />

    <!-- Y-axis Labels -->
    <text x="${padding.left - 6}" y="${padding.top + 4}" text-anchor="end" fill="#94a3b8" font-size="10" font-family="monospace">${Math.round(maxEle)}m</text>
    <text x="${padding.left - 6}" y="${padding.top + chartH}" text-anchor="end" fill="#94a3b8" font-size="10" font-family="monospace">${Math.round(minEle)}m</text>

    <!-- X-axis Labels -->
    <text x="${padding.left}" y="${height - 6}" text-anchor="start" fill="#94a3b8" font-size="10" font-family="monospace">0 km</text>
    <text x="${padding.left + chartW * 0.5}" y="${height - 6}" text-anchor="middle" fill="#64748b" font-size="10" font-family="monospace">${(maxDist * 0.5).toFixed(1)} km</text>
    <text x="${padding.left + chartW}" y="${height - 6}" text-anchor="end" fill="#94a3b8" font-size="10" font-family="monospace">${maxDist.toFixed(1)} km</text>

    <!-- Area & Line Profile -->
    <path d="${areaPath}" fill="url(#elevationGrad)" />
    <path d="${linePath}" fill="none" stroke="#38bdf8" stroke-width="2.2" stroke-linejoin="round" />

    <!-- Hover Indicator Elements -->
    <line id="hoverLine" x1="0" y1="${padding.top}" x2="0" y2="${padding.top + chartH}" stroke="#f8fafc" stroke-width="1.2" stroke-dasharray="3 3" style="display:none;" />
    <circle id="hoverDot" cx="0" cy="0" r="4.5" fill="#38bdf8" stroke="#ffffff" stroke-width="2" style="display:none;" />
  `;
}

function clearElevationCanvas() {
  const svg = document.getElementById("elevationSvg");
  if (!svg) return;
  svg.innerHTML = `
    <defs>
      <linearGradient id="elevationGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.45" />
        <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.02" />
      </linearGradient>
    </defs>
    <text x="300" y="55" text-anchor="middle" fill="#64748b" font-size="12" font-family="sans-serif">No route elevation loaded</text>
  `;
}

function handleElevationHover(e) {
  if (!state.currentParsed || !state.currentParsed.elevations || state.currentParsed.elevations.length < 2) return;

  const svg = document.getElementById("elevationSvg");
  if (!svg) return;
  const rect = svg.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const ratio = Math.max(0, Math.min(1, mouseX / rect.width));

  const elevations = state.currentParsed.elevations;
  const coords = state.currentParsed.coordinates;
  const index = Math.floor(ratio * (elevations.length - 1));
  const currentPt = elevations[index];

  if (currentPt) {
    const eleDisplay = currentPt.ele !== null && !isNaN(currentPt.ele) ? `${Math.round(currentPt.ele)}m` : "--";
    document.getElementById("elevationHoverInfo").textContent = `${currentPt.dist.toFixed(1)} km | ${eleDisplay}`;

    const width = 600;
    const height = 110;
    const padding = { top: 12, right: 15, bottom: 22, left: 42 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;
    const maxDist = elevations[elevations.length - 1].dist || 1;

    const validEles = elevations.filter((e) => e.ele !== null && !isNaN(e.ele)).map((e) => e.ele);
    let minEle = validEles.length > 0 ? Math.min(...validEles) : 0;
    let maxEle = validEles.length > 0 ? Math.max(...validEles) : 100;
    if (maxEle - minEle < 10) {
      minEle = Math.max(0, minEle - 10);
      maxEle = maxEle + 10;
    }
    const eleRange = maxEle - minEle;

    const svgX = padding.left + (currentPt.dist / maxDist) * chartW;
    const currentEleVal = currentPt.ele !== null && !isNaN(currentPt.ele) ? currentPt.ele : minEle;
    const svgY = padding.top + chartH - ((currentEleVal - minEle) / eleRange) * chartH;

    const hoverLine = document.getElementById("hoverLine");
    const hoverDot = document.getElementById("hoverDot");
    if (hoverLine && hoverDot) {
      hoverLine.setAttribute("x1", svgX);
      hoverLine.setAttribute("x2", svgX);
      hoverLine.style.display = "block";

      hoverDot.setAttribute("cx", svgX);
      hoverDot.setAttribute("cy", svgY);
      hoverDot.style.display = "block";
    }

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
