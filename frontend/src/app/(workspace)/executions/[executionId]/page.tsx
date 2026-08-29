import { redirect } from "next/navigation";

import { legacyStoryLookup } from "@/features/story/presentation-api";

export default async function LegacyExecutionDetail({
  params,
}: {
  params: Promise<{ executionId: string }>;
}) {
  const { executionId } = await params;
  redirect(
    legacyStoryLookup[executionId] ? `/stories/${legacyStoryLookup[executionId]}` : "/stories",
  );
}
