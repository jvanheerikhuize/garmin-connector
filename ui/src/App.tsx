import { useEffect, useState } from 'react';
import { ConnectionStatus } from './components/ConnectionStatus';

interface DeviceState {
  connected: boolean;
  modelName: string | null;
  mountPoint: string | null;
}

export default function App() {
  const [device, setDevice] = useState<DeviceState>({
    connected: false,
    modelName: null,
    mountPoint: null,
  });

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    const connect = () => {
      ws = new WebSocket(`ws://${window.location.host}/api/ws`);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'device_status') {
            setDevice(data.payload);
          }
        } catch (e) {
          console.error("Failed to parse WS message", e);
        }
      };

      ws.onclose = () => {
        setDevice({ connected: false, modelName: null, mountPoint: null });
        reconnectTimeout = setTimeout(connect, 2000);
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white font-mono flex flex-col">
      <header className="flex justify-between items-center p-4 border-b border-gray-700">
        <h1 className="text-xl font-bold text-cyan-400">Garmin Connector</h1>
        <div className="flex items-center gap-4">
          {device.modelName && <span className="text-sm">{device.modelName}</span>}
          <ConnectionStatus connected={device.connected} />
        </div>
      </header>
      <main className="flex-1 p-8 flex items-center justify-center">
        {device.connected ? (
          <div className="text-center">
            <h2 className="text-2xl mb-4 text-green-400">Device Ready</h2>
            <p className="text-gray-400">Workspace conditionally rendered here.</p>
          </div>
        ) : (
          <div className="text-center">
            <h2 className="text-2xl mb-4 text-red-400">Waiting for Device</h2>
            <div className="w-full h-1 bg-gradient-to-r from-red-500 via-transparent to-red-500 animate-pulse"></div>
          </div>
        )}
      </main>
    </div>
  );
}
