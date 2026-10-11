const API_URL = process.env.API_URL ?? "http://localhost:8000";

type Health = { status: string; service: string; env: string };

async function getHealth(): Promise<Health | null> {
  try {
    const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok ? ((await res.json()) as Health) : null;
  } catch {
    return null;
  }
}

export async function ApiStatus() {
  const health = await getHealth();
  return health ? (
    <p className="text-emerald-600">
      API online · {health.service} ({health.env})
    </p>
  ) : (
    <p className="text-amber-600">API unreachable at {API_URL}</p>
  );
}
