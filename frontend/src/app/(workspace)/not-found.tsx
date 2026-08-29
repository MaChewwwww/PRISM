import Link from "next/link";

import { EmptyState } from "@/components/product/workspace-ui";

export default function WorkspaceNotFound() {
  return (
    <>
      <EmptyState
        title="Story not found"
        detail="This identifier is not part of the fixed illustrative storytelling dataset."
      />
      <Link className="detail-link return-link" href="/">
        Return to overview
      </Link>
    </>
  );
}
