let map;
let trackLayer;
let selectedSport = "cycling";
let courseToDelete = null;

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Leaflet Map
  map = L.map('map', {
    zoomControl: true,
    attributionControl: true
  }).setView([51.505, -0.09], 4);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(map);

  // Map starts disabled and reset until watch connection is established
  disableAndResetMap();

  // Setup Sport Selector Buttons
  const sportButtons = document.querySelectorAll(".sport-btn");
  sportButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      sportButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedSport = btn.getAttribute("data-sport") || "cycling";
    });
  });

  // Setup Ingest Modal
  const btnOpenIngestModal = document.getElementById("btnOpenIngestModal");
  const ingestModal = document.getElementById("ingestModal");
  const ingestModalClose = document.getElementById("ingestModalClose");
  const btnCancelIngest = document.getElementById("btnCancelIngest");

  const openIngestModal = () => {
    if (!btnOpenIngestModal.disabled) {
      ingestModal.classList.add("cyber-modal--open");
    }
  };

  const closeIngestModal = () => {
    ingestModal.classList.remove("cyber-modal--open");
  };

  btnOpenIngestModal.addEventListener("click", openIngestModal);
  ingestModalClose.addEventListener("click", closeIngestModal);
  btnCancelIngest.addEventListener("click", closeIngestModal);

  ingestModal.addEventListener("click", (e) => {
    if (e.target === ingestModal) {
      closeIngestModal();
    }
  });

  // Setup File Upload & DropZone
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");

  dropZone.addEventListener("click", () => {
    if (dropZone.style.pointerEvents !== "none") {
      fileInput.click();
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (dropZone.style.pointerEvents !== "none") {
      dropZone.classList.add("drag-over");
    }
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer && e.dataTransfer.files.length) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length) {
      handleFileUpload(e.target.files[0]);
      fileInput.value = "";
    }
  });

  // Setup Delete Confirmation Modal
  const confirmModal = document.getElementById("confirmModal");
  const confirmModalClose = document.getElementById("confirmModalClose");
  const btnConfirmCancel = document.getElementById("btnConfirmCancel");
  const btnConfirmDelete = document.getElementById("btnConfirmDelete");

  const closeConfirmModal = () => {
    confirmModal.classList.remove("cyber-modal--open");
    courseToDelete = null;
  };

  confirmModalClose.addEventListener("click", closeConfirmModal);
  btnConfirmCancel.addEventListener("click", closeConfirmModal);

  confirmModal.addEventListener("click", (e) => {
    if (e.target === confirmModal) {
      closeConfirmModal();
    }
  });

  btnConfirmDelete.addEventListener("click", performDeleteCourse);

  // Global Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeIngestModal();
      closeConfirmModal();
    }
  });

  // Start Device Status Polling
  checkDeviceStatus();
  setInterval(checkDeviceStatus, 3000);
});

function disableAndResetMap() {
  if (trackLayer) {
    map.removeLayer(trackLayer);
    trackLayer = null;
  }
  map.setView([51.505, -0.09], 4);

  if (map.dragging) map.dragging.disable();
  if (map.touchZoom) map.touchZoom.disable();
  if (map.doubleClickZoom) map.doubleClickZoom.disable();
  if (map.scrollWheelZoom) map.scrollWheelZoom.disable();
  if (map.boxZoom) map.boxZoom.disable();
  if (map.keyboard) map.keyboard.disable();

  const container = document.querySelector(".map-viewport-container");
  if (container) container.classList.add("map-disabled");

  const overlay = document.getElementById("mapEmptyOverlay");
  if (overlay) {
    overlay.style.display = "flex";
    const textEl = overlay.querySelector(".empty-overlay-content");
    if (textEl) textEl.innerText = "Connect watch via USB to enable route preview";
  }

  const mapInfo = document.getElementById("mapInfo");
  if (mapInfo) mapInfo.innerText = "No watch connected";
}

function enableMap() {
  if (map.dragging) map.dragging.enable();
  if (map.touchZoom) map.touchZoom.enable();
  if (map.doubleClickZoom) map.doubleClickZoom.enable();
  if (map.scrollWheelZoom) map.scrollWheelZoom.enable();
  if (map.boxZoom) map.boxZoom.enable();
  if (map.keyboard) map.keyboard.enable();

  const container = document.querySelector(".map-viewport-container");
  if (container) container.classList.remove("map-disabled");

  const overlay = document.getElementById("mapEmptyOverlay");
  const mapInfo = document.getElementById("mapInfo");

  if (!trackLayer) {
    if (overlay) {
      overlay.style.display = "flex";
      const textEl = overlay.querySelector(".empty-overlay-content");
      if (textEl) textEl.innerText = "Select a course to preview route";
    }
    if (mapInfo && mapInfo.innerText === "No watch connected") {
      mapInfo.innerText = "No route selected";
    }
  } else {
    if (overlay) overlay.style.display = "none";
  }
}

let missingCycles = 0;
let lastKnownState = "disconnected"; // "connected", "mounting", "disconnected"

async function checkDeviceStatus() {
  try {
    const res = await fetch("/api/device");
    const data = await res.json();
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("deviceStatus");
    const btnRefresh = document.getElementById("btnRefresh");
    const btnOpenIngestModal = document.getElementById("btnOpenIngestModal");
    const dropZone = document.getElementById("dropZone");

    if (data.connected) {
      missingCycles = 0;
      lastKnownState = "connected";
      dot.className = "status-dot connected";
      // Course counts will be populated by fetchCourses()
      if (!text.innerText.includes("courses")) {
          text.innerText = `Connected: ${data.model_name || 'Garmin Watch'}`;
      }
      
      btnRefresh.disabled = false;
      btnOpenIngestModal.disabled = false;
      dropZone.style.opacity = "1";
      dropZone.style.pointerEvents = "auto";

      enableMap();

      const listContainer = document.getElementById("courseTableBody");
      if (listContainer.querySelector(".empty-courses")) {
        fetchCourses();
      }
    } else {
      if (data.mounting) {
        missingCycles = 0;
        lastKnownState = "mounting";
        
        btnRefresh.disabled = true;
        btnOpenIngestModal.disabled = true;
        dropZone.style.opacity = "0.5";
        dropZone.style.pointerEvents = "none";
        
        text.innerText = "Watch detected, waiting for storage mount...";
        dot.className = "status-dot";
        dot.style.backgroundColor = "orange";
        document.getElementById("courseTableBody").innerHTML = `
          <div class="empty-courses">Device detected. Waiting for OS to mount storage...</div>
        `;
        disableAndResetMap();
      } else {
        // Disconnected state
        if (lastKnownState !== "disconnected" && missingCycles < 7) {
          missingCycles++;
          // Skip UI update to smooth over temporary USB re-enumerations
          return;
        }
        
        lastKnownState = "disconnected";
        dot.className = "status-dot disconnected";
        
        btnRefresh.disabled = true;
        btnOpenIngestModal.disabled = true;
        dropZone.style.opacity = "0.5";
        dropZone.style.pointerEvents = "none";
        
        text.innerText = "No watch connected";
        dot.style.backgroundColor = ""; // Reset inline style
        document.getElementById("courseTableBody").innerHTML = `
          <div class="empty-courses">No device connected. Connect watch via USB to view storage.</div>
        `;
        disableAndResetMap();
      }
    }
  } catch (e) {
    if (lastKnownState !== "disconnected" && missingCycles < 7) {
      missingCycles++;
      return;
    }
    lastKnownState = "disconnected";
    console.error("Failed to check device status:", e);
    disableAndResetMap();
  }
}

async function handleFileUpload(file) {
  const dropZone = document.getElementById("dropZone");
  const ingestModal = document.getElementById("ingestModal");
  if (dropZone.style.pointerEvents === "none") return;

  if (!file.name.toLowerCase().endsWith(".gpx")) {
    showMessage("Only .gpx files are supported for ingestion.", "error");
    return;
  }

  showMessage(`Ingesting ${file.name} for ${selectedSport}...`, "warning");

  const reader = new FileReader();
  reader.onload = async (e) => {
    const content = e.target.result;
    try {
      const res = await fetch("/api/sideload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gpx_content: content,
          course_name: file.name.replace(/\.gpx$/i, ""),
          sport: selectedSport
        })
      });

      const data = await res.json();
      if (data.success) {
        showMessage(`Successfully converted & sideloaded: ${data.filename}`, "success");
        setTimeout(() => {
          ingestModal.classList.remove("cyber-modal--open");
        }, 500);
        fetchCourses();
        checkDeviceStatus();
      } else {
        showMessage(`Ingestion failed: ${data.error}`, "error");
      }
    } catch (err) {
      showMessage(`Network error: ${err.message}`, "error");
    }
  };
  reader.readAsText(file);
}

async function fetchCourses() {
  try {
    const res = await fetch("/api/courses");
    const data = await res.json();
    const listBody = document.getElementById("courseTableBody");

    const text = document.getElementById("deviceStatus");
    if (!data.courses || data.courses.length === 0) {
      listBody.innerHTML = '<div class="empty-courses">No courses found in watch storage</div>';
      if (text.innerText.startsWith("Connected")) {
         const modelName = text.innerText.split("(")[0].trim().replace("Connected: ", "");
         text.innerText = `Connected: ${modelName} (0 courses)`;
      }
      return;
    }
    
    if (text.innerText.startsWith("Connected")) {
       const stagedCount = data.courses.filter(c => c.location.toUpperCase().includes("NEWFILES")).length;
       const coursesCount = data.courses.filter(c => c.location.toUpperCase().includes("COURSES")).length;
       const total = stagedCount + coursesCount;
       const pendingStr = stagedCount > 0 ? ` (${stagedCount} pending sync)` : "";
       const modelName = text.innerText.split("(")[0].trim().replace("Connected: ", "");
       text.innerText = `Connected: ${modelName} (${total} courses${pendingStr})`;
    }

    listBody.innerHTML = data.courses.map(c => {
      const isFit = c.filename.toLowerCase().endsWith('.fit');
      const formatClass = isFit ? 'course-format-fit' : 'course-format-gpx';
      const formatLabel = isFit ? 'FIT' : 'GPX';
      const sizeKb = Math.round(c.size_bytes / 1024);
      const displayPath = c.watch_path || `/GARMIN/Courses/${c.filename}`;
      const fullPath = c.full_path || displayPath;

      return `
        <div class="course-row">
          <div class="course-row-left">
            <span class="course-format-badge ${formatClass}">${formatLabel}</span>
            <div class="course-details">
              <div class="course-path" title="${fullPath}">${displayPath}</div>
              <div class="course-meta">${sizeKb} KB</div>
            </div>
          </div>
          <div class="course-actions">
            <button class="btn btn-sm btn-primary" onclick="mapCourse('${c.filename}')">Map</button>
            <button class="btn btn-sm btn-danger" onclick="deleteCourse('${c.filename}')">Delete</button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error("Failed to fetch courses:", err);
  }
}

function deleteCourse(filename) {
  courseToDelete = filename;
  const modalText = document.getElementById("confirmModalText");
  modalText.innerText = `Are you sure you want to delete '${filename}' from the Garmin watch storage?`;
  
  const modal = document.getElementById("confirmModal");
  modal.classList.add("cyber-modal--open");
}

async function performDeleteCourse() {
  if (!courseToDelete) return;
  const filename = courseToDelete;
  
  const modal = document.getElementById("confirmModal");
  modal.classList.remove("cyber-modal--open");
  courseToDelete = null;

  try {
    const res = await fetch(`/api/courses/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    if (res.ok) {
      if (trackLayer) {
        map.removeLayer(trackLayer);
        trackLayer = null;
      }
      const overlay = document.getElementById("mapEmptyOverlay");
      if (overlay) {
        overlay.style.display = "flex";
        const textEl = overlay.querySelector(".empty-overlay-content");
        if (textEl) textEl.innerText = "Select a course to preview route";
      }
      document.getElementById("mapInfo").innerText = "No route selected";
      
      fetchCourses();
      checkDeviceStatus();
      showMessage(`Deleted ${filename}`, "success");
    } else {
      showMessage(`Failed to delete ${filename}`, "error");
    }
  } catch (err) {
    showMessage(`Delete failed: ${err.message}`, "error");
  }
}

async function mapCourse(filename) {
  const mapInfo = document.getElementById("mapInfo");
  const overlay = document.getElementById("mapEmptyOverlay");

  try {
    mapInfo.innerText = `Loading route for ${filename}...`;

    const res = await fetch(`/api/fetch-course/${encodeURIComponent(filename)}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error);

    const pts = data.points;
    if (trackLayer) {
      map.removeLayer(trackLayer);
      trackLayer = null;
    }

    if (pts && pts.length > 0) {
      trackLayer = L.polyline(pts, {
        color: '#00f0ff',
        weight: 4,
        opacity: 0.9,
        className: 'glowing-track'
      }).addTo(map);

      map.fitBounds(trackLayer.getBounds(), { padding: [30, 30] });
      if (overlay) overlay.style.display = "none";
      mapInfo.innerText = `Showing: ${filename} (${pts.length} trackpoints)`;
    } else {
      if (overlay) {
        overlay.style.display = "flex";
        const textEl = overlay.querySelector(".empty-overlay-content");
        if (textEl) textEl.innerText = `No GPS trackpoints found in ${filename}`;
      }
      mapInfo.innerText = `No GPS trackpoints found in ${filename}`;
    }
  } catch (err) {
    if (overlay) {
      overlay.style.display = "flex";
      const textEl = overlay.querySelector(".empty-overlay-content");
      if (textEl) textEl.innerText = `Failed to load route: ${err.message}`;
    }
    mapInfo.innerText = `Failed to load route: ${err.message}`;
    showMessage(`Failed to map course: ${err.message}`, "error");
  }
}

function showMessage(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");

  const alertClass = type === "success" 
    ? "cyber-alert--success" 
    : type === "error" 
      ? "cyber-alert--error" 
      : "cyber-alert--warning";

  const titleText = type === "success" ? "Success" : type === "error" ? "Error" : "Notice";

  toast.className = `cyber-alert ${alertClass} cyber-toast`;
  toast.innerHTML = `
    <div class="cyber-alert__title">${titleText}</div>
    <div style="font-size: 0.85rem; font-family: var(--font-mono);">${msg}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "toastSlideOut 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}
