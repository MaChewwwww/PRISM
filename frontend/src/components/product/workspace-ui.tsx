import { AlertTriangle, ArrowRight, FlaskConical, LockKeyhole } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import type { Provenance } from "@/features/story/story-data";

export function DemoDataNotice() {
  return (
    <div className="demo-notice" role="note">
      <FlaskConical aria-hidden="true" />
      <div>
        <strong>Illustrative story</strong>
        <span>
          Fixed illustrative market, portfolio, agent, and usage data. No provider request was made.
        </span>
      </div>
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </header>
  );
}

export function Section({
  title,
  description,
  children,
  id,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section className="content-section" aria-labelledby={id}>
      <div className="content-section-heading">
        <h2 id={id}>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {children}
    </section>
  );
}

export function StateBadge({ state }: { state: string }) {
  const normalized = state.toLowerCase().replaceAll("_", "-");
  return (
    <span className="state-badge" data-state={normalized}>
      {state.replaceAll("_", " ")}
    </span>
  );
}

const provenanceLabels: Record<Provenance, string> = {
  "active-portfolio": "Active Portfolio",
  "shadow-portfolio": "Shadow Portfolio",
  "market-benchmark": "Market Benchmark",
  "illustrative-paper": "Active Portfolio",
  simulated: "Shadow Portfolio",
  "planned-integration": "Planned Integration",
};

export function ProvenanceLabel({ provenance }: { provenance: Provenance }) {
  return (
    <span className="provenance-label" data-provenance={provenance}>
      {provenanceLabels[provenance] ?? provenance}
    </span>
  );
}

export function MetricStrip({
  metrics,
}: {
  metrics: Array<{ label: string; value: string; detail?: string }>;
}) {
  return (
    <dl className="metric-strip">
      {metrics.map((metric) => (
        <div key={metric.label}>
          <dt>{metric.label}</dt>
          <dd>{metric.value}</dd>
          {metric.detail && <span>{metric.detail}</span>}
        </div>
      ))}
    </dl>
  );
}

export function DisabledAction({ label, reason }: { label: string; reason: string }) {
  return (
    <div className="disabled-action">
      <button type="button" disabled aria-describedby={`reason-${label.replaceAll(" ", "-")}`}>
        <LockKeyhole aria-hidden="true" /> {label}
      </button>
      <span id={`reason-${label.replaceAll(" ", "-")}`}>{reason}</span>
    </div>
  );
}

export function KeyValueList({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <dl className="key-value-list">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function DetailLink({ href, label = "Open detail" }: { href: string; label?: string }) {
  return (
    <Link className="detail-link" href={href}>
      {label} <ArrowRight aria-hidden="true" />
    </Link>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <AlertTriangle aria-hidden="true" />
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}
