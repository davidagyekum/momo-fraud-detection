import { useQuery } from "@tanstack/react-query";
import { LogOut, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/use-auth";
import { Alert, Skeleton } from "../components/feedback";
import { Dialog } from "../components/overlays";
import { Button, Surface } from "../components/primitives";
import type { PortalUser } from "../types/api";

export function ProfilePage(): React.ReactNode {
  const auth = useAuth();
  const navigate = useNavigate();
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [logoutBusy, setLogoutBusy] = useState(false);
  const profile = useQuery({
    queryKey: ["current-staff-profile"],
    queryFn: async () => (await auth.request<PortalUser>("/me")).data,
    staleTime: 60_000,
  });

  const signOut = async (): Promise<void> => {
    setLogoutBusy(true);
    try {
      await auth.signOut();
      void navigate("/login", { replace: true });
    } finally {
      setLogoutBusy(false);
    }
  };

  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Profile / Security</h1>
          <p>Current staff identity and browser-session protection.</p>
        </div>
      </header>
      {profile.isPending ? (
        <Skeleton lines={4} label="Loading staff profile" />
      ) : null}
      {profile.isError ? (
        <Alert tone="danger" live>
          The profile could not be refreshed. Session protection remains active.
        </Alert>
      ) : null}
      {profile.data ? (
        <Surface className="profile-grid">
          <div>
            <span>Full name</span>
            <strong>{profile.data.full_name}</strong>
          </div>
          <div>
            <span>Work email</span>
            <strong>{profile.data.email}</strong>
          </div>
          <div>
            <span>Roles</span>
            <strong>{profile.data.roles.join(", ")}</strong>
          </div>
          <div>
            <span>Account status</span>
            <strong>{profile.data.status}</strong>
          </div>
        </Surface>
      ) : null}
      <Alert tone="success" title="Browser session protected">
        <ShieldCheck size={18} aria-hidden="true" /> Access tokens remain in
        memory; refresh credentials remain in an HTTP-only cookie.
      </Alert>
      <div>
        <Button
          variant="danger"
          icon={<LogOut />}
          onClick={() => setLogoutOpen(true)}
        >
          Sign out
        </Button>
      </div>
      <Dialog
        open={logoutOpen}
        title="Sign out of the staff portal?"
        onClose={() => setLogoutOpen(false)}
        footer={
          <>
            <Button variant="ghost" onClick={() => setLogoutOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={logoutBusy}
              onClick={() => void signOut()}
            >
              Sign out
            </Button>
          </>
        }
      >
        <p>The current refresh session will be revoked.</p>
      </Dialog>
    </div>
  );
}
