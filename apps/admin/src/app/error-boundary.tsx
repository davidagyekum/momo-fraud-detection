import {
  Component,
  type ErrorInfo,
  type PropsWithChildren,
  type ReactNode,
} from "react";
import { StatePanel } from "../components/feedback";

interface ErrorState {
  failed: boolean;
}

export class GlobalErrorBoundary extends Component<
  PropsWithChildren,
  ErrorState
> {
  state: ErrorState = { failed: false };

  static getDerivedStateFromError(): ErrorState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV)
      console.error("Portal render failure", error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.failed) {
      return (
        <main className="error-page">
          <StatePanel
            kind="error"
            title="The portal could not render this page"
            description="Reload the page. If the problem continues, share the request or build identifier with support."
            actionLabel="Reload portal"
            onAction={() => window.location.reload()}
          />
        </main>
      );
    }
    return this.props.children;
  }
}
