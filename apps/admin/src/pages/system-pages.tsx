import { ArrowLeft, LogOut } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/use-auth";
import { StatePanel } from "../components/feedback";
import { Button } from "../components/primitives";

export function NoAccessPage(): React.ReactNode {
  const auth = useAuth();
  const navigate = useNavigate();
  return (
    <main className="standalone-state">
      <StatePanel
        kind="permission"
        title="You do not have access to this staff area"
        description="Navigation visibility does not grant permission. Ask an authorised administrator if your role should change."
      />
      {auth.phase === "authenticated" ? (
        <Button
          variant="secondary"
          icon={<LogOut />}
          onClick={() =>
            void auth
              .signOut()
              .then(() => navigate("/login", { replace: true }))
          }
        >
          Sign out
        </Button>
      ) : (
        <Link to="/login" className="button button--secondary">
          Return to sign in
        </Link>
      )}
    </main>
  );
}

export function NotFoundPage(): React.ReactNode {
  return (
    <main className="standalone-state">
      <StatePanel
        kind="error"
        title="Page not found"
        description="The portal route may have moved or you may not have been given a valid link."
      />
      <Link to="/dashboard" className="button button--secondary">
        <ArrowLeft size={18} aria-hidden="true" /> Return to dashboard
      </Link>
    </main>
  );
}
