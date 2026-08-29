import { redirect } from "next/navigation";

import { legacyAlternativeLookup } from "@/features/story/presentation-api";

export default async function LegacyShadowFundDetail({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  redirect(
    legacyAlternativeLookup[sessionId]
      ? `/alternatives/${legacyAlternativeLookup[sessionId]}`
      : "/alternatives",
  );
}
