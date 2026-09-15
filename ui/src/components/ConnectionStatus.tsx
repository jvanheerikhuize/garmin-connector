

export function ConnectionStatus({ connected }: { connected: boolean }) {
  const baseClasses = "inline-block w-3 h-3 rounded-full mr-2";
  const statusClasses = connected
    ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,1)]"
    : "bg-red-500 opacity-50";

  return (
    <div className="flex items-center text-sm font-mono uppercase">
      <span className={`${baseClasses} ${statusClasses}`}></span>
      {connected ? "Connected" : "Disconnected"}
    </div>
  );
}
