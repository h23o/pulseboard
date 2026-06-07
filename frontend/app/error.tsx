"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const isDbError =
    error.message?.includes("connect") ||
    error.message?.includes("ECONNREFUSED") ||
    error.message?.includes("postgres");

  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-8 text-center shadow-sm">
        <div className="mb-3 text-3xl">⚠️</div>
        <h2 className="mb-2 text-lg font-semibold text-red-800">
          {isDbError ? "Database Unavailable" : "Something went wrong"}
        </h2>
        <p className="mb-4 text-sm text-red-700">
          {isDbError
            ? "PulseBoard could not connect to PostgreSQL. Make sure the Docker container is running: docker compose up -d"
            : error.message ?? "An unexpected error occurred."}
        </p>
        <button
          onClick={reset}
          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
