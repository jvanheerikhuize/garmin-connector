import re
with open("garmin_connector/gui/static/index.html", "r") as f:
    content = f.read()

toast_css = """
    /* Toast Styles */
    #toastContainer { position: fixed; bottom: 20px; right: 20px; display: flex; flex-direction: column; gap: 10px; z-index: 9999; }
    .toast { background: #313244; border-left: 4px solid #89b4fa; padding: 12px 20px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); animation: slideIn 0.3s ease forwards; max-width: 300px; display: flex; align-items: center; gap: 10px; }
    .toast.success { border-color: #a6e3a1; }
    .toast.error { border-color: #f38ba8; }
    @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    @keyframes fadeOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
  </style>
"""
content = content.replace("</style>", toast_css)

toast_div = """
  <div id="toastContainer"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
"""
content = content.replace('<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>', toast_div)

with open("garmin_connector/gui/static/index.html", "w") as f:
    f.write(content)
