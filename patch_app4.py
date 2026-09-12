import re
with open("garmin_connector/gui/static/app.js", "r") as f:
    content = f.read()

content = content.replace('async function handleFileUpload(file) {', 'async function handleFileUpload(file) {\n  if (document.getElementById("dropZone").classList.contains("disabled")) return;')

with open("garmin_connector/gui/static/app.js", "w") as f:
    f.write(content)
