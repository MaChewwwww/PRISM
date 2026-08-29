import { redirect } from "next/navigation";

import { legacyStoryLookup } from "@/features/story/story-data";

export default async function LegacyAuditDetail({
  params,
}: {
  params: Promise<{ traceId: string }>;
}) {
  const { traceId } = await params;
  redirect(legacyStoryLookup[traceId] ? `/stories/${legacyStoryLookup[traceId]}` : "/stories");
}
