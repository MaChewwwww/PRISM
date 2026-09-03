"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState, type ReactNode } from "react";

const DEFAULT_PAGE_SIZE = 8;

/**
 * Client-side paginated list. Renders items per page and supports optional
 * smooth scrolling to top on page change.
 * Used for the portfolio activity ledger, orders receipts panel, and ShadowFund session lists.
 */
export function PaginatedList<T>({
  items,
  renderItem,
  getKey,
  className,
  itemLabel = "items",
  pageSize = DEFAULT_PAGE_SIZE,
  scrollToTop = true,
  navClassName,
}: {
  items: T[];
  renderItem: (item: T) => ReactNode;
  getKey: (item: T, index: number) => string;
  /** Applied to the <ul> wrapping the page's items. */
  className?: string;
  /** Plural noun used in the pagination summary (e.g. "sessions"). */
  itemLabel?: string;
  /** Number of items per page. Defaults to 8. */
  pageSize?: number;
  /** Whether to scroll to top of window on page change. Defaults to true. */
  scrollToTop?: boolean;
  /** Optional custom styling for the <nav> element. */
  navClassName?: string;
}) {
  const [page, setPage] = useState(1);

  const effectivePageSize = Math.max(1, pageSize);
  const totalPages = Math.max(1, Math.ceil(items.length / effectivePageSize));
  const safePage = Math.min(page, totalPages);
  const pageItems = items.slice((safePage - 1) * effectivePageSize, safePage * effectivePageSize);

  function goToPage(next: number) {
    setPage(next);
    if (scrollToTop && typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  return (
    <>
      <ul className={className}>
        {pageItems.map((item, index) => (
          <li key={getKey(item, (safePage - 1) * effectivePageSize + index)}>{renderItem(item)}</li>
        ))}
      </ul>

      {items.length > effectivePageSize && (
        <nav
          className={navClassName ?? "mt-5 flex items-center justify-between gap-3"}
          aria-label="Pagination"
        >
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
