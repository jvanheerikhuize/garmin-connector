let map, trackLayer;

document.addEventListener("DOMContentLoaded", () => {
  map = L.map('map').setView([50, 6], 4);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

  checkDeviceStatus();
  setInterval(checkDeviceStatus, 3000);

  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const ingestModal = document.getElementById("ingestModal");
  const btnIngest = document.getElementById("btnIngest");
  const modalClose = document.getElementById("modalClose");

  btnIngest.addEventListener("click", () => ingestModal.classList.remove("hidden"));
  modalClose.addEventListener("click", () => ingestModal.classList.add("hidden"));
  ingestModal.addEventListener("click", (e) => {
    if (e.target === ingestModal) ingestModal.classList.add("hidden");
  });

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
    const btnIngest = document.getElementById("btnIngest");

    if (data.connected) {
      dot.classList.add("connected");
      text.innerText = `Connected to ${data.model_name} (ID: ${data.unit_id}) - ${data.courses_count} courses`;
      btnRefresh.disabled = false;
      btnIngest.disabled = false;

      const tbody = document.getElementById("courseTableBody");
      if (tbody.children.length === 1 && (tbody.innerText.includes("No courses") || tbody.innerText.includes("No device"))) {
        fetchCourses();
      }
    } else {
      dot.classList.remove("connected");
      text.innerText = "No device connected. Please plug in your Garmin watch.";
      btnRefresh.disabled = true;
      btnIngest.disabled = true;
      document.getElementById("courseTableBody").innerHTML = '<tr><td colspan="4">No device connected</td></tr>';
    }
  } catch (e) {
    console.error("Failed to check device", e);
  }
}

async function handleFileUpload(file) {
  if (document.getElementById("btnIngest").disabled) return;
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
        document.getElementById("ingestModal").classList.add("hidden");
        fetchCourses();
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
    const tbody = document.getElementById("courseTableBody");
    if (!data.courses || data.courses.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4">No courses on watch</td></tr>';
      return;
    }
    
    tbody.innerHTML = data.courses.map(c => `
      <tr>
        <td>${c.filename}</td>
        <td>${Math.round(c.size_bytes / 1024)} KB</td>
        <td>${c.location}</td>
        <td>
          <a onclick="mapCourse(\'${c.filename}\')">Map</a> | 
          <a onclick="deleteCourse('${c.filename}')">Delete</a>
        </td>
      </tr>
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
      trackLayer = L.polyline(pts, {color: '#f38ba8', weight: 4}).addTo(map);
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
  const icon = type === "success" ? "✔" : type === "error" ? "✖" : "ℹ";
  toast.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "fadeOut 0.3s ease forwards";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
