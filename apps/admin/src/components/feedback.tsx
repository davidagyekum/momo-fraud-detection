import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  CircleHelp,
  Inbox,
  Info,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import type { PropsWithChildren, ReactNode } from "react";
import { Button } from "./primitives";

type Tone = "info" | "success" | "warning" | "danger" | "neutral";

const toneIcon: Record<Tone, ReactNode> = {
  info: <Info size={20} />,
  success: <CheckCircle2 size={20} />,
  warning: <AlertTriangle size={20} />,
  danger: <ShieldAlert size={20} />,
  neutral: <CircleHelp size={20} />,
};

export function Alert({
  tone = "info",
  title,
  children,
  live = false,
}: PropsWithChildren<{
  tone?: Tone;
  title?: string;
  live?: boolean;
}>): React.ReactNode {
  return (
    <div className={`alert alert--${tone}`} role={live ? "alert" : "status"}>
      <span className="alert__icon" aria-hidden="true">
        {toneIcon[tone]}
      </span>
      <div>
        {title ? <strong>{title}</strong> : null}
        <div>{children}</div>
      </div>
    </div>
  );
}

export function StatusBadge({
  tone,
  children,
}: PropsWithChildren<{ tone: Tone }>) {
  return (
    <span className={`status-badge status-badge--${tone}`}>
      <span aria-hidden="true">{toneIcon[tone]}</span>
      <span>{children}</span>
    </span>
  );
}

export function Skeleton({
  lines = 3,
  label = "Loading content",
}: {
  lines?: number;
  label?: string;
}) {
  return (
    <div className="skeleton" role="status" aria-label={label}>
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} className="skeleton__line" />
      ))}
    </div>
  );
}

interface StatePanelProps {
  kind?: "empty" | "error" | "permission";
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  requestId?: string | null;
}

export function StatePanel({
  kind = "empty",
  title,
  description,
  actionLabel,
  onAction,
  requestId,
}: StatePanelProps): React.ReactNode {
  const Icon =
    kind === "error" ? AlertTriangle : kind === "permission" ? Ban : Inbox;
  return (
    <div
      className={`state-panel state-panel--${kind}`}
      role={kind === "error" ? "alert" : "status"}
    >
      <Icon size={42} strokeWidth={1.6} aria-hidden="true" />
      <h2>{title}</h2>
      <p>{description}</p>
      {requestId ? (
        <p className="state-panel__request">Request ID: {requestId}</p>
      ) : null}
      {actionLabel && onAction ? (
        <Button
          variant="secondary"
          icon={<RefreshCw size={18} />}
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}

export function ChartContainer({
  title,
  summary,
  children,
  tableAlternative,
}: PropsWithChildren<{
  title: string;
  summary: string;
  tableAlternative?: ReactNode;
}>): React.ReactNode {
  return (
    <section
      className="chart-container"
      aria-labelledby={`${title.replaceAll(" ", "-")}-title`}
    >
      <h2 id={`${title.replaceAll(" ", "-")}-title`}>{title}</h2>
      <p className="sr-only">{summary}</p>
      <div aria-hidden="true">{children}</div>
      {tableAlternative ? (
        <div className="chart-container__alternative">{tableAlternative}</div>
      ) : null}
    </section>
  );
}
