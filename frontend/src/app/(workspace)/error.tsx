"use client";

import { EmptyState } from "@/components/product/workspace-ui";

export default function WorkspaceError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <>
      <EmptyState
        title="Story workspace unavailable"
        detail="The requested view could not be rendered. No authorization or execution action was attempted."
      />
      <button className="retry-button" type="button" onClick={reset}>
        Try again
      </button>
    </>
  );
}
