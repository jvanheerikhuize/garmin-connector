---
id: connection-status-shell
title: Connection Status Shell
tier: skeleton
status: implemented
owners: [jerry]
depends_on: [gui-bootstrap]
last_updated: 2026-09-15
---

# Connection Status Shell

`ui/src/App.tsx` and `ui/src/components/ConnectionStatus.tsx`

Depends on: [gui-bootstrap](gui-bootstrap.md).

## Purpose

The minimum frontend needed to prove the walking skeleton end-to-end: load a React page, establish a WebSocket connection with the Go server, and reflect the watch's connection status truthfully and continuously in real-time.

## Scope

**In scope:** React app shell, WebSocket context/hook, header status component, and conditional rendering of the main application workspace.

## Requirements

### Page shell markup (`App.tsx`)
- MUST render a header containing a brand title (Cyberpunk aesthetic) and a connection status indicator component.
- MUST conditionally render the `Workspace` component only when a device is connected. Otherwise, it renders a `WaitingForDevice` cyberpunk scanline view.

### Device status syncing (`useWebSocket` hook)
- MUST connect to `ws://<host>:<port>/api/ws` on mount.
- MUST handle incoming `device_status` payloads and update React state (`connected`, `modelName`, `mountPoint`).
- MUST automatically attempt to reconnect with backoff if the WebSocket connection drops.
- A "disconnected" state instantly removes the course list and disables the map preview.
- A "connected" state triggers a fetch to `/api/courses` (owned by the course management feature).

### Status dot styling (`ConnectionStatus.tsx`)
- Driven entirely by React component state and Tailwind CSS classes:
  - Connected: glowing green dot (`bg-green-500 shadow-[0_0_8px_rgba(34,197,94,1)]`).
  - Disconnected: neutral/red dot (`bg-red-500 opacity-50`).

## Data Shapes / Interfaces

React Context / State:
```typescript
interface DeviceState {
  connected: boolean;
  modelName: string | null;
  mountPoint: string | null;
}
```

WebSocket Messages:
```typescript
interface WsMessage {
  type: "device_status" | "error";
  payload: any;
}
```
