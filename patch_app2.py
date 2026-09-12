import re
with open("garmin_connector/gui/static/app.js", "r") as f:
    content = f.read()

# Add showMessage function
show_message_func = """
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
"""

content = content + show_message_func

# Replace alert(...) with showMessage(...)
content = re.sub(r'alert\("Only GPX files are supported in MVP\."\);', 'showMessage("Only GPX files are supported.", "error");', content)
content = re.sub(r'alert\("Successfully sideloaded!"\);', 'showMessage("Successfully sideloaded!", "success");', content)
content = re.sub(r'alert\("Failed to sideload: " \+ data\.error\);', 'showMessage("Failed to sideload: " + data.error, "error");', content)
content = re.sub(r'alert\("Error: " \+ err\.message\);', 'showMessage("Error: " + err.message, "error");', content)
content = re.sub(r'alert\("Delete failed"\);', 'showMessage("Delete failed", "error");', content)
content = re.sub(r'alert\("Failed to map course: " \+ err\.message\);', 'showMessage("Failed to map course: " + err.message, "error");', content)

# Remove mapInfo error overwriting which looks ugly, or convert it to a neutral message
content = re.sub(r'document\.getElementById\("mapInfo"\)\.innerText = "Failed to load\.";', '', content)

with open("garmin_connector/gui/static/app.js", "w") as f:
    f.write(content)
