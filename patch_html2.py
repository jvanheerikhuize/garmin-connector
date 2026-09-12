import re
with open("garmin_connector/gui/static/index.html", "r") as f:
    content = f.read()

# CSS additions
css_additions = """    button:hover:not(:disabled) { background: #74c7ec; }
    button:disabled { background: #45475a; color: #a6adc8; cursor: not-allowed; }
    #dropZone.disabled { opacity: 0.5; pointer-events: none; border-color: #45475a; cursor: not-allowed; }
    a { color: #89b4fa; cursor: pointer; text-decoration: underline; }"""
content = re.sub(r'button:hover \{ background: #74c7ec; \}\n.*?a \{ color: #89b4fa; cursor: pointer; text-decoration: underline; \}', css_additions, content, flags=re.DOTALL)

# Button addition
content = content.replace('<button onclick="fetchCourses()">Refresh List</button>', '<button id="btnRefresh" onclick="fetchCourses()" disabled>Refresh List</button>')

# Make dropzone initially disabled
content = content.replace('<div id="dropZone">', '<div id="dropZone" class="disabled">')

with open("garmin_connector/gui/static/index.html", "w") as f:
    f.write(content)
