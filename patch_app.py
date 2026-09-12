import re
with open("garmin_connector/gui/static/app.js", "r") as f:
    content = f.read()

# Update fetchCourses Map button to show for both
content = re.sub(r'\$\{c\.filename\.toLowerCase\(\)\.endsWith\(\'\.gpx\'\) \? `<a onclick="mapCourse\(\'\$\{c\.filename\}\'\)">Map</a> \| ` : \'\'\}',
                 r'<a onclick="mapCourse(\'${c.filename}\')">Map</a> | ', content)

# Update mapCourse to handle the JSON points
new_mapcourse = """async function mapCourse(filename) {
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
}"""

content = re.sub(r'async function mapCourse\(filename\) \{.*\}', new_mapcourse, content, flags=re.DOTALL)

with open("garmin_connector/gui/static/app.js", "w") as f:
    f.write(content)
