import { useEffect } from "react";
import type { ReactNode } from "react";

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-night/40 p-4"
      onClick={onClose}
    >
      <div
        // Stops a click inside the panel from bubbling to the backdrop and
        // closing it — only clicking the actual backdrop (or Escape/Cancel)
        // should dismiss the modal.
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl bg-white p-4 shadow-lg"
      >
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-night/40">{title}</p>
          <button
            type="button"
            onClick={onClose}
            className="text-night/40 hover:text-night"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
