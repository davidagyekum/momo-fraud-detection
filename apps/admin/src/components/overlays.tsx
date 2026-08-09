import { X } from "lucide-react";
import {
  useEffect,
  useId,
  useRef,
  type PropsWithChildren,
  type ReactNode,
} from "react";
import { Button } from "./primitives";

const focusableSelector =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

interface OverlayProps extends PropsWithChildren {
  open: boolean;
  title: string;
  onClose: () => void;
  mode: "dialog" | "drawer";
  footer?: ReactNode;
}

function OverlayPanel({
  open,
  title,
  onClose,
  mode,
  footer,
  children,
}: OverlayProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    panel?.querySelector<HTMLElement>(focusableSelector)?.focus();

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !panel) return;
      const focusable = [
        ...panel.querySelectorAll<HTMLElement>(focusableSelector),
      ];
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [onClose, open]);

  if (!open) return null;
  return (
    <div className={`overlay overlay--${mode}`}>
      <button
        className="overlay__backdrop"
        aria-hidden="true"
        tabIndex={-1}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        className={`overlay__panel overlay__panel--${mode}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="overlay__header">
          <h2 id={titleId}>{title}</h2>
          <Button
            variant="ghost"
            aria-label={`Close ${title}`}
            onClick={onClose}
            icon={<X />}
          >
            Close
          </Button>
        </header>
        <div className="overlay__body">{children}</div>
        {footer ? <footer className="overlay__footer">{footer}</footer> : null}
      </div>
    </div>
  );
}

export function Dialog(props: Omit<OverlayProps, "mode">): React.ReactNode {
  return <OverlayPanel {...props} mode="dialog" />;
}

export function Drawer(props: Omit<OverlayProps, "mode">): React.ReactNode {
  return <OverlayPanel {...props} mode="drawer" />;
}
