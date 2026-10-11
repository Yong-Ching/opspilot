import { Suspense } from "react";

import { ApiStatus } from "./api-status";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-4 px-4">
      <h1 className="text-3xl font-semibold tracking-tight">OpsPilot</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        AI operations copilot for Acme Market. Walking skeleton.
      </p>
      <Suspense fallback={<p className="text-zinc-500">Checking API…</p>}>
        <ApiStatus />
      </Suspense>
    </main>
  );
}
