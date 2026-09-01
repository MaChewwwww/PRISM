import Link from "next/link";

import { EmptyState } from "@/components/workspace/workspace-ui";

export default function WorkspaceNotFound() {
  return (
    <>
      <EmptyState
        title="Story not found"
        detail="No recorded monitoring data exists for this identifier."
      />
      <Link className="detail-link return-link" href="/">
        Return to overview
      </Link>
    </>
  );
}
