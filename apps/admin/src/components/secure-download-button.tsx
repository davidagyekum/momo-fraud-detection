import { Download } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../auth/use-auth";
import { Alert } from "./feedback";
import { Button } from "./primitives";

export function SecureDownloadButton({
  path,
  filename,
  children,
}: {
  path: string;
  filename: string;
  children: React.ReactNode;
}): React.ReactNode {
  const auth = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = async (): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      await auth.download(path, filename);
    } catch {
      setError(
        "The private file could not be downloaded. Check your permission and try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="secure-download">
      <Button
        variant="secondary"
        loading={busy}
        icon={<Download size={18} />}
        onClick={() => void download()}
      >
        {children}
      </Button>
      {error ? (
        <Alert tone="danger" live>
          {error}
        </Alert>
      ) : null}
    </div>
  );
}
