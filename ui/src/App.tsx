import { useEffect, useState, useRef } from 'react';
import { ConnectionStatus } from './components/ConnectionStatus';
import { MapContainer, TileLayer, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface DeviceState {
  connected: boolean;
  modelName: string | null;
  mountPoint: string | null;
}

interface Course {
  filename: string;
  full_path: string;
  size_bytes: number;
  location: string;
}

function MapUpdater({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) {
      map.fitBounds(points as any);
    }
  }, [points, map]);
  return null;
}

export default function App() {
  const [device, setDevice] = useState<DeviceState>({ connected: false, modelName: null, mountPoint: null });
  const [courses, setCourses] = useState<Course[]>([]);
  const [points, setPoints] = useState<[number, number][]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    const connect = () => {
      ws = new WebSocket(`ws://${window.location.host}/api/ws`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'device_status') setDevice(data.payload);
        } catch (e) {}
      };
      ws.onclose = () => setTimeout(connect, 2000);
    };
    connect();
    return () => ws?.close();
  }, []);

  const fetchCourses = async () => {
    const res = await fetch('/api/courses');
    const data = await res.json();
    if (data.connected) setCourses(data.courses);
  };

  useEffect(() => {
    if (device.connected) fetchCourses();
  }, [device.connected]);

  const loadPreview = async (filename: string) => {
    setSelectedCourse(filename);
    const res = await fetch(`/api/fetch-course/${filename}`);
    const data = await res.json();
    if (data.success) setPoints(data.points);
  };

  const deleteCourse = async (filename: string) => {
    if (!confirm(`Delete ${filename}?`)) return;
    await fetch(`/api/courses/${filename}`, { method: 'DELETE' });
    if (selectedCourse === filename) {
      setPoints([]);
      setSelectedCourse(null);
    }
    fetchCourses();
  };

  const fileInputRef = useRef<HTMLInputElement>(null);
  const handleUpload = async (e: any) => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    await fetch('/api/sideload', {
      method: 'POST',
      body: JSON.stringify({ gpx_content: text, course_name: file.name.replace('.gpx', ''), sport: 'cycling' })
    });
    fetchCourses();
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex justify-between p-4 border-b border-app-border bg-app-panel">
        <h1 className="text-xl font-display text-cyber-cyan">Garmin Connector</h1>
        <div className="flex items-center gap-4 text-cyber-chrome-200">
          {device.modelName && <span>{device.modelName}</span>}
          <ConnectionStatus connected={device.connected} />
        </div>
      </header>
      <main className="flex-1 p-4 grid grid-cols-1 md:grid-cols-[300px_1fr] gap-4">
        {device.connected ? (
          <>
            <div className="bg-app-panel border border-app-border p-4 shadow-panel flex flex-col gap-4">
              <h2 className="text-cyber-green font-mono uppercase tracking-widest text-sm">Watch Storage</h2>
              <button onClick={() => fileInputRef.current?.click()} className="border border-cyber-cyan text-cyber-cyan bg-[rgba(0,240,255,0.08)] py-2 font-mono hover:bg-cyber-cyan hover:text-black hover:shadow-glow-cyan transition-all">Ingest Route</button>
              <input type="file" hidden ref={fileInputRef} accept=".gpx" onChange={handleUpload} />
              
              <div className="flex flex-col gap-2 overflow-y-auto">
                {courses.map(c => (
                  <div key={c.filename} className="text-xs font-mono p-2 border border-cyber-chrome-500 rounded bg-app-subpanel">
                    <div className="truncate text-cyber-chrome-200">{c.filename}</div>
                    <div className="text-cyber-chrome-400 mb-2 truncate">{c.location}</div>
                    <div className="flex gap-2">
                      <button onClick={() => loadPreview(c.filename)} className="text-cyber-cyan hover:underline">Preview</button>
                      <button onClick={() => deleteCourse(c.filename)} className="text-cyber-magenta hover:underline">Delete</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-app-panel border border-app-border shadow-panel relative flex flex-col">
              <div className="absolute top-4 left-4 z-[400] text-cyber-cyan font-mono text-sm mix-blend-difference">
                {selectedCourse ? selectedCourse : 'No course selected'}
              </div>
              <div className="flex-1 h-full w-full">
                <MapContainer center={[51.505, -0.09]} zoom={4} style={{ height: '100%', width: '100%', background: '#050608' }}>
                  <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
                  {points.length > 0 && <Polyline positions={points} pathOptions={{ color: '#00f0ff', weight: 4 }} className="glowing-track" />}
                  {points.length > 0 && <MapUpdater points={points} />}
                </MapContainer>
              </div>
            </div>
          </>
        ) : (
          <div className="col-span-full flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-2xl mb-4 font-mono text-cyber-magenta opacity-80 uppercase tracking-widest">Waiting for Device</h2>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
