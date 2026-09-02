import { redirect } from "next/navigation";

// The catalyst feed now lives on the Market Tracker page. Keep this route as a
// permanent redirect so existing links and bookmarks continue to work.
export default function NewsPage() {
  redirect("/market-tracker");
}
