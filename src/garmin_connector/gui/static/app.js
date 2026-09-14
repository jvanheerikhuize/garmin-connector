let lastKnownState = "disconnected";
let missingCycles = 0;
let mapInstance = null;
let currentTrackLayer = null;
let selectedSport = "cycling";
let courseToDelete = null;

// DOM Elements
const statusDot = document.getElementById("statusDot");
const deviceStatus = document.getElementById("deviceStatus");
const mapInfo = document.getElementById("mapInfo");
const mapEmptyOverlay = document.getElementById("mapEmptyOverlay");
const mapViewport = document.querySelector(".map-viewport-container");
const courseTableBody = document.getElementById("courseTableBody");
const btnOpenIngestModal = document.getElementById("btnOpenIngestModal");
const btnRefresh = document.getElementById("btnRefresh");
const toastContainer = document.getElementById("toastContainer");
const ingestModal = document.getElementById("ingestModal");
const confirmModal = document.getElementById("confirmModal");
const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    setupEventListeners();
    checkDeviceStatus();
    setInterval(checkDeviceStatus, 3000);
});

// --- Modals & Toasts ---
function showMessage(msg, type = "warning") {
    if (!["success", "error", "warning"].includes(type)) type = "warning";
    const toast = document.createElement("div");
    toast.className = `cyber-alert cyber-alert--${type} cyber-toast`;
    
    const title = document.createElement("div");
    title.className = "cyber-alert__title";
    title.innerText = type.toUpperCase();
    
    const body = document.createElement("div");
    body.style.fontSize = "0.85rem";
    body.style.fontFamily = "var(--font-mono)";
    body.innerText = msg;
    
    toast.appendChild(title);
    toast.appendChild(body);
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = "toastSlideOut 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards";
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

function openModal(modal) {
    modal.classList.add("cyber-modal--open");
}

function closeModal(modal) {
    modal.classList.remove("cyber-modal--open");
}

function closeAllModals() {
    closeModal(ingestModal);
    closeModal(confirmModal);
}

// --- Map Logic ---
function initMap() {
    mapInstance = L.map('map', {
        zoomControl: true,
        attributionControl: true
    }).setView([51.505, -0.09], 4);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
    }).addTo(mapInstance);
    
    disableAndResetMap();
}

window.disableAndResetMap = function() {
    if (currentTrackLayer) {
        mapInstance.removeLayer(currentTrackLayer);
        currentTrackLayer = null;
    }
    mapInstance.setView([51.505, -0.09], 4);
    mapInstance.dragging.disable();
    mapInstance.touchZoom.disable();
    mapInstance.doubleClickZoom.disable();
    mapInstance.scrollWheelZoom.disable();
    mapInstance.boxZoom.disable();
    mapInstance.keyboard.disable();
    
    mapViewport.classList.add("map-disabled");
    mapEmptyOverlay.style.display = "flex";
    mapEmptyOverlay.querySelector('.empty-overlay-content').innerText = "Connect watch via USB to enable route preview";
    mapInfo.innerText = "No watch connected";
    
    btnOpenIngestModal.disabled = true;
    btnRefresh.disabled = true;
};

window.enableMap = function() {
    mapInstance.dragging.enable();
    mapInstance.touchZoom.enable();
    mapInstance.doubleClickZoom.enable();
    mapInstance.scrollWheelZoom.enable();
    mapInstance.boxZoom.enable();
    mapInstance.keyboard.enable();
    
    mapViewport.classList.remove("map-disabled");
    btnOpenIngestModal.disabled = false;
    btnRefresh.disabled = false;
    
    if (!currentTrackLayer) {
        mapEmptyOverlay.style.display = "flex";
        mapEmptyOverlay.querySelector('.empty-overlay-content').innerText = "Select a course to preview route";
        if (mapInfo.innerText === "No watch connected") {
            mapInfo.innerText = "No route selected";
        }
    } else {
        mapEmptyOverlay.style.display = "none";
    }
};

function mapCourse(filename) {
    mapInfo.innerText = "Loading route...";
    fetch(`/api/fetch-course/${encodeURIComponent(filename)}`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) throw new Error(data.error);
            
            if (currentTrackLayer) {
                mapInstance.removeLayer(currentTrackLayer);
                currentTrackLayer = null;
            }
            
            const points = data.points;
            if (points.length === 0) {
                mapEmptyOverlay.style.display = "flex";
                mapEmptyOverlay.querySelector('.empty-overlay-content').innerText = `No GPS trackpoints found in ${filename}`;
                mapInfo.innerText = `No GPS trackpoints found in ${filename}`;
            } else {
                currentTrackLayer = L.polyline(points, {
                    className: 'glowing-track',
                    weight: 4,
                    opacity: 0.9,
                    color: '#00f0ff'
                }).addTo(mapInstance);
                mapInstance.fitBounds(currentTrackLayer.getBounds(), { padding: [30, 30] });
                mapEmptyOverlay.style.display = "none";
                mapInfo.innerText = `Showing: ${filename} (${points.length} trackpoints)`;
            }
        })
        .catch(err => {
            mapEmptyOverlay.style.display = "flex";
            mapEmptyOverlay.querySelector('.empty-overlay-content').innerText = `Failed to load route: ${err.message}`;
            mapInfo.innerText = `Failed to load route: ${err.message}`;
            showMessage(`Failed to load route: ${err.message}`, "error");
        });
}

// --- Status & Courses ---
function checkDeviceStatus() {
    fetch("/api/device")
        .then(res => {
            if (!res.ok) throw new Error("Network error");
            return res.json();
        })
        .then(data => {
            if (data.connected) {
                missingCycles = 0;
                lastKnownState = "connected";
                statusDot.className = "status-dot connected";
                
                if (!deviceStatus.innerText.includes("courses")) {
                    deviceStatus.innerText = `Connected: ${data.model_name || "Garmin Watch"}`;
                }
                
                enableMap();
                if (courseTableBody.querySelector('.empty-courses') && 
                    courseTableBody.querySelector('.empty-courses').innerText.includes("Awaiting")) {
                    fetchCourses();
                }
            } else if (data.mounting) {
                missingCycles = 0;
                lastKnownState = "mounting";
                statusDot.className = "status-dot mounting";
                deviceStatus.innerText = "Watch detected, waiting for storage mount...";
                disableAndResetMap();
            } else {
                handleDisconnected();
            }
        })
        .catch(err => handleDisconnected(err));
}

function handleDisconnected(err = null) {
    if (lastKnownState !== "disconnected" && missingCycles < 7) {
        missingCycles++;
        return;
    }
    missingCycles++;
    lastKnownState = "disconnected";
    statusDot.className = "status-dot disconnected";
    deviceStatus.innerText = "No watch connected";
    disableAndResetMap();
    courseTableBody.innerHTML = '<div class="empty-courses">Awaiting device connection...</div>';
    if (err) console.error("Polling error:", err);
}

window.fetchCourses = function() {
    fetch("/api/courses")
        .then(res => res.json())
        .then(data => {
            if (!data.connected) return;
            
            const courses = data.courses;
            courseTableBody.innerHTML = "";
            
            if (courses.length === 0) {
                courseTableBody.innerHTML = '<div class="empty-courses">No courses found in watch storage</div>';
                if (deviceStatus.innerText.startsWith("Connected")) {
                    const model = deviceStatus.innerText.split('(')[0].trim();
                    deviceStatus.innerText = `${model} (0 courses)`;
                }
                return;
            }
            
            let coursesCount = 0;
            let pendingCount = 0;
            
            courses.forEach(c => {
                if (c.location.toUpperCase().includes("NEWFILES")) pendingCount++;
                else coursesCount++;
                
                const row = document.createElement("div");
                row.className = "course-row";
                
                const isFit = c.filename.toLowerCase().endsWith(".fit");
                const badgeClass = isFit ? "course-format-fit" : "course-format-gpx";
                const badgeText = isFit ? "FIT" : "GPX";
                const sizeKb = Math.round(c.size_bytes / 1024);
                
                row.innerHTML = `
                    <div class="course-row-left">
                        <div class="course-format-badge ${badgeClass}">${badgeText}</div>
                        <div class="course-details">
                            <div class="course-path" title="${c.full_path}">${c.watch_path || `/GARMIN/Courses/${c.filename}`}</div>
                            <div class="course-meta">${sizeKb} KB • ${c.location}</div>
                        </div>
                    </div>
                    <div class="course-actions">
                        <button class="btn btn-sm btn-primary map-btn" data-file="${c.filename}">Map</button>
                        <button class="btn btn-sm btn-danger del-btn" data-file="${c.filename}">Delete</button>
                    </div>
                `;
                courseTableBody.appendChild(row);
            });
            
            if (deviceStatus.innerText.startsWith("Connected")) {
                const model = deviceStatus.innerText.split('(')[0].trim();
                let txt = `${model} (${coursesCount + pendingCount} courses`;
                if (pendingCount > 0) txt += `, ${pendingCount} pending sync`;
                txt += `)`;
                deviceStatus.innerText = txt;
            }
        })
        .catch(err => console.error("Fetch courses error:", err));
};

// --- Events ---
function setupEventListeners() {
    btnRefresh.addEventListener("click", fetchCourses);
    
    // Ingest Modal
    btnOpenIngestModal.addEventListener("click", () => openModal(ingestModal));
    document.getElementById("ingestModalClose").addEventListener("click", () => closeModal(ingestModal));
    document.getElementById("btnCancelIngest").addEventListener("click", () => closeModal(ingestModal));
    
    // Sport Pills
    document.querySelectorAll(".sport-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".sport-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            selectedSport = e.target.getAttribute("data-sport");
        });
    });
    
    // Dropzone
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", e => {
        e.preventDefault();
        if (!btnOpenIngestModal.disabled) dropZone.classList.add("drag-over");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
    dropZone.addEventListener("drop", e => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        if (btnOpenIngestModal.disabled) return;
        if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener("change", e => {
        if (e.target.files.length) handleFileUpload(e.target.files[0]);
        fileInput.value = "";
    });
    
    // Course Actions (Delegated)
    courseTableBody.addEventListener("click", e => {
        const mapBtn = e.target.closest(".map-btn");
        if (mapBtn) {
            mapCourse(mapBtn.getAttribute("data-file"));
        }
        
        const delBtn = e.target.closest(".del-btn");
        if (delBtn) {
            courseToDelete = delBtn.getAttribute("data-file");
            document.getElementById("confirmModalText").innerText = `Are you sure you want to delete ${courseToDelete}?`;
            openModal(confirmModal);
        }
    });
    
    // Delete Modal
    document.getElementById("confirmModalClose").addEventListener("click", () => {
        closeModal(confirmModal);
        courseToDelete = null;
    });
    document.getElementById("btnConfirmCancel").addEventListener("click", () => {
        closeModal(confirmModal);
        courseToDelete = null;
    });
    document.getElementById("btnConfirmDelete").addEventListener("click", () => {
        if (!courseToDelete) return;
        const filename = courseToDelete;
        closeModal(confirmModal);
        
        fetch(`/api/courses/${encodeURIComponent(filename)}`, { method: "DELETE" })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showMessage(`Deleted ${filename}`, "success");
                    if (mapInfo.innerText.includes(filename)) {
                        if (currentTrackLayer) {
                            mapInstance.removeLayer(currentTrackLayer);
                            currentTrackLayer = null;
                        }
                        mapEmptyOverlay.style.display = "flex";
                        mapEmptyOverlay.querySelector('.empty-overlay-content').innerText = "Select a course to preview route";
                        mapInfo.innerText = "No route selected";
                    }
                    fetchCourses();
                    checkDeviceStatus();
                } else {
                    showMessage(`Failed to delete ${filename}: ${data.error || 'Unknown error'}`, "error");
                }
            })
            .catch(err => showMessage(`Delete failed: ${err.message}`, "error"));
            
        courseToDelete = null;
    });
    
    // Global close
    window.addEventListener("keydown", e => {
        if (e.key === "Escape") closeAllModals();
    });
    
    [ingestModal, confirmModal].forEach(m => {
        m.addEventListener("click", e => {
            if (e.target === m) closeModal(m);
        });
    });
}

function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith(".gpx")) {
        showMessage("Only .gpx files are supported", "error");
        return;
    }
    
    showMessage(`Ingesting ${file.name} for ${selectedSport}...`, "warning");
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        let courseName = file.name;
        if (courseName.toLowerCase().endsWith(".gpx")) courseName = courseName.substring(0, courseName.length - 4);
        
        fetch("/api/sideload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                gpx_content: content,
                course_name: courseName,
                sport: selectedSport
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showMessage(`Successfully converted & sideloaded: ${data.filename}`, "success");
                setTimeout(() => closeModal(ingestModal), 500);
                fetchCourses();
                checkDeviceStatus();
            } else {
                showMessage(data.error || "Unknown error", "error");
            }
        })
        .catch(err => showMessage(`Network error: ${err.message}`, "error"));
    };
    reader.onerror = () => showMessage("Failed to read file", "error");
    reader.readAsText(file);
}
