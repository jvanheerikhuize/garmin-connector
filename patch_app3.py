import re
with open("garmin_connector/gui/static/app.js", "r") as f:
    content = f.read()

new_func = """async function checkDeviceStatus() {
  try {
    const res = await fetch("/api/device");
    const data = await res.json();
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("deviceStatus");
    const btnRefresh = document.getElementById("btnRefresh");
    const dropZone = document.getElementById("dropZone");
    
    if (data.connected) {
      dot.classList.add("connected");
      text.innerText = `Connected to ${data.model_name} (ID: ${data.unit_id}) - ${data.courses_count} courses`;
      btnRefresh.disabled = false;
      dropZone.classList.remove("disabled");
      
      const tbody = document.getElementById("courseTableBody");
      if (tbody.children.length === 1 && (tbody.innerText.includes("No courses") || tbody.innerText.includes("No device"))) {
        fetchCourses();
      }
    } else {
      dot.classList.remove("connected");
      text.innerText = "No device connected. Please plug in your Garmin watch.";
      btnRefresh.disabled = true;
      dropZone.classList.add("disabled");
      document.getElementById("courseTableBody").innerHTML = '<tr><td colspan="4">No device connected</td></tr>';
    }
  } catch (e) {
    console.error("Failed to check device", e);
  }
}"""

content = re.sub(r'async function checkDeviceStatus\(\) \{.*?\}\n\}', new_func, content, flags=re.DOTALL)

with open("garmin_connector/gui/static/app.js", "w") as f:
    f.write(content)
