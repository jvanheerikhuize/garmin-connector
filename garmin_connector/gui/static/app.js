let map, trackLayer;

document.addEventListener("DOMContentLoaded", () => {
  map = L.map('map').setView([50, 6], 4);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 20
  }).addTo(map);

  checkDeviceStatus();
  setInterval(checkDeviceStatus, 3000);

  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");


  const confirmModal = document.getElementById("confirmModal");
  const confirmModalClose = document.getElementById("confirmModalClose");
  const btnConfirmCancel = document.getElementById("btnConfirmCancel");
  const btnConfirmDelete = document.getElementById("btnConfirmDelete");

  const closeConfirmModal = () => {
    confirmModal.classList.add("hidden");
    courseToDelete = null;
  };

  confirmModalClose.addEventListener("click", closeConfirmModal);
  btnConfirmCancel.addEventListener("click", closeConfirmModal);
  
  confirmModal.addEventListener("click", (e) => {
    if (e.target === confirmModal) closeConfirmModal();
  });

  btnConfirmDelete.addEventListener("click", performDeleteCourse);

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) handleFileUpload(e.target.files[0]);
  });
});

async function checkDeviceStatus() {
  try {
    const res = await fetch("/api/device");
    const data = await res.json();
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("deviceStatus");
    const btnRefresh = document.getElementById("btnRefresh");
    const dropZone = document.getElementById("dropZone");

    if (data.connected) {
      dot.classList.add("connected");
      const total = data.courses_count + data.staged_count;
      const pendingStr = data.staged_count > 0 ? ` (${data.staged_count} pending sync)` : "";
      text.innerText = `Connected to ${data.model_name} (ID: ${data.unit_id}) - ${total} courses${pendingStr}`;
      btnRefresh.disabled = false;
      dropZone.style.opacity = "1";
      dropZone.style.pointerEvents = "auto";

      const tbody = document.getElementById("courseTableBody");
      if (tbody.children.length === 1 && (tbody.innerText.includes("No courses") || tbody.innerText.includes("No device"))) {
        fetchCourses();
      }
    } else {
      dot.classList.remove("connected");
      text.innerText = "No device connected. Please plug in your Garmin watch.";
      btnRefresh.disabled = true;
      dropZone.style.opacity = "0.5";
      dropZone.style.pointerEvents = "none";
      document.getElementById("courseTableBody").innerHTML = '<div class="empty-state">No device connected</div>';
    }
  } catch (e) {
    console.error("Failed to check device", e);
  }
}

async function handleFileUpload(file) {
  const dropZone = document.getElementById("dropZone");
  if (dropZone.style.pointerEvents === "none") return;
  
  if (!file.name.toLowerCase().endsWith(".gpx")) {
    showMessage("Only GPX files are supported.", "error");
    return;
  }
  const reader = new FileReader();
  reader.onload = async (e) => {
    const content = e.target.result;
    try {
      const res = await fetch("/api/sideload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gpx_content: content, course_name: file.name.replace(".gpx", ""), sport: "cycling" })
      });
      const data = await res.json();
      if (data.success) {
        showMessage("Successfully sideloaded!", "success");
        fetchCourses();
        checkDeviceStatus();
      } else {
        showMessage("Failed to sideload: " + data.error, "error");
      }
    } catch (err) {
      showMessage("Error: " + err.message, "error");
    }
  };
  reader.readAsText(file);
}

async function fetchCourses() {
  try {
    const res = await fetch("/api/courses");
    const data = await res.json();
    const listBody = document.getElementById("courseTableBody");
    if (!data.courses || data.courses.length === 0) {
      listBody.innerHTML = '<div class="empty-state">No courses on watch</div>';
      return;
    }
    
    listBody.innerHTML = data.courses.map(c => `
      <div class="course-card">
        <div class="course-icon">${c.filename.endsWith('.fit') ? '' : ''}</div>
        <div class="course-info">
          <div class="course-name">${c.filename}</div>
          <div class="course-meta">${Math.round(c.size_bytes / 1024)} KB &bull; ${c.location}</div>
        </div>
        <div class="course-actions">
          <button class="btn btn-primary btn-small" onclick="mapCourse('${c.filename}')">Map</button>
          <button class="btn btn-danger btn-small" onclick="deleteCourse('${c.filename}')">Del</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error(err);
  }
}

let courseToDelete = null;

function deleteCourse(filename) {
  courseToDelete = filename;
  document.getElementById("confirmModalText").innerText = `Are you sure you want to delete ${filename}?`;
  document.getElementById("confirmModal").classList.remove("hidden");
}

async function performDeleteCourse() {
  if (!courseToDelete) return;
  const filename = courseToDelete;
  document.getElementById("confirmModal").classList.add("hidden");
  courseToDelete = null;

  try {
    const res = await fetch(`/api/courses/${filename}`, { method: 'DELETE' });
    if (res.ok) {
      if (trackLayer) map.removeLayer(trackLayer);
      document.getElementById("mapInfo").innerText = "Select a course to preview";
      fetchCourses();
      checkDeviceStatus();
      showMessage(`Deleted ${filename}`, "success");
    } else {
      showMessage("Delete failed", "error");
    }
  } catch (err) {
    showMessage("Delete failed", "error");
  }
}

async function mapCourse(filename) {
  try {
    document.getElementById("mapInfo").innerText = `Loading ${filename}...`;
    const res = await fetch(`/api/fetch-course/${encodeURIComponent(filename)}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error);
    
    const pts = data.points;
    if (trackLayer) map.removeLayer(trackLayer);
    
    if (pts && pts.length > 0) {
      trackLayer = L.polyline(pts, {
        color: '#00ff00', 
        weight: 4, 
        opacity: 0.8,
        className: 'glowing-track'
      }).addTo(map);
      map.fitBounds(trackLayer.getBounds());
      document.getElementById("mapInfo").innerText = `Previewing ${filename} (${pts.length} points)`;
    } else {
      document.getElementById("mapInfo").innerText = `No track points found in ${filename}`;
    }
  } catch (err) {
    showMessage("Failed to map course: " + err.message, "error");
    
  }
}

function showMessage(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icon = type === "success" ? "" : type === "error" ? "" : "";
  toast.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "fadeOut 0.3s ease forwards";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
