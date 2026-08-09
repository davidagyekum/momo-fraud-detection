import { ReceiptText } from "lucide-react";

export function BrandMark({
  compact = false,
}: {
  compact?: boolean;
}): React.ReactNode {
  return (
    <span className="brand-mark" aria-label="MoMo-FDVS">
      <span className="brand-mark__icon" aria-hidden="true">
        <ReceiptText size={compact ? 22 : 28} strokeWidth={1.8} />
      </span>
      <span className="brand-mark__text">MoMo-FDVS</span>
    </span>
  );
}
