import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-start justify-center px-4">
      <h1 className="text-2xl font-bold">This page doesn't exist</h1>
      <p className="mt-2 text-muted">Check the address, or go back to the start.</p>
      <Link to="/" className="btn-primary mt-6 no-underline">
        Go to the home page
      </Link>
    </div>
  );
}
