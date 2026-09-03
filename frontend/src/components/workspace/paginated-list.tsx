"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState, type ReactNode } from "react";

const PAGE_SIZE = 8;

/**
 * Client-side paginated list. Renders up to 8 items per page and, on page
 * change, smoothly scrolls the window to the top so the new items are visible.
 * Used for the portfolio activity ledger and ShadowFund session lists.
 */
export function PaginatedList<T>({
  items,
  renderItem,
  getKey,
  className,
  itemLabel = "items",
}: {
  items: T[];
  renderItem: (item: T) => ReactNode;
  getKey: (item: T) => string;
  /** Applied to the <ul> wrapping the page's items. */
  className?: string;
  /** Plural noun used in the pagination summary (e.g. "sessions"). */
  itemLabel?: string;
}) {
  const [page, setPage] = useState(1);

  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = items.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function goToPage(next: number) {
    setPage(next);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  return (
    <>
      <ul className={className}>
        {pageItems.map((item) => (
          <li key={getKey(item)}>{renderItem(item)}</li>
        ))}
      </ul>

      {items.length > PAGE_SIZE && (
        <nav className="mt-5 flex items-center justify-between gap-3" aria-label="Pagination">
          <span className="font-mono text-[11px] text-[#64748B]">
            Page {safePage} of {totalPages} · {items.length} {itemLabel}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => goToPage(Math.max(1, safePage - 1))}
              disabled={safePage <= 1}
              className="inline-flex items-center gap-1 rounded-md border border-white/8 bg-white/5 px-3 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" /> Prev
            </button>
            <button
              type="button"
              onClick={() => goToPage(Math.min(totalPages, safePage + 1))}
              disabled={safePage >= totalPages}
              className="inline-flex items-center gap-1 rounded-md border border-white/8 bg-white/5 px-3 py-1.5 text-[12px] font-medium text-[#CBD5E1] outline-none transition-colors hover:border-[#547D83]/40 hover:text-[#F8FAFC] focus-visible:ring-2 focus-visible:ring-[#547D83] disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        </nav>
      )}
    </>
  );
}
