let map, trackLayer;

document.addEventListener("DOMContentLoaded", () => {
  map = L.map('map').setView([50, 6], 4);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

  checkDeviceStatus();
  setInterval(checkDeviceStatus, 3000);

  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("hover"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("hover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("hover");
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
    if (data.connected) {
      dot.classList.add("connected");
      text.innerText = `Connected to ${data.model_name} (ID: ${data.unit_id}) - ${data.courses_count} courses`;
      if (document.getElementById("courseTableBody").children.length === 1 && document.getElementById("courseTableBody").innerText.includes("No courses")) {
        fetchCourses();
      }
    } else {
      dot.classList.remove("connected");
      text.innerText = "No device connected. Please plug in your Garmin watch.";
    }
  } catch (e) {
    console.error("Failed to check device", e);
  }
}

async function handleFileUpload(file) {
  if (!file.name.toLowerCase().endsWith(".gpx")) {
    alert("Only GPX files are supported in MVP.");
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
        alert("Successfully sideloaded!");
        fetchCourses();
      } else {
        alert("Failed to sideload: " + data.error);
      }
    } catch (err) {
      alert("Error: " + err.message);
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

async function deleteCourse(filename) {
  if (!confirm(`Delete ${filename}?`)) return;
  try {
    const res = await fetch(`/api/courses/${filename}`, { method: 'DELETE' });
    if (res.ok) fetchCourses();
  } catch (err) {
    alert("Delete failed");
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
    alert("Failed to map course: " + err.message);
    document.getElementById("mapInfo").innerText = "Failed to load.";
  }
}
