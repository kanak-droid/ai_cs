import { useRef } from "react";

interface PhotoUploadButtonProps {
  onSelect: (file: File, previewUrl: string) => void;
  disabled?: boolean;
}

export function PhotoUploadButton({ onSelect, disabled }: PhotoUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    onSelect(file, URL.createObjectURL(file));
    event.target.value = "";
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*,video/*"
        className="hidden"
        onChange={handleChange}
        aria-hidden="true"
        tabIndex={-1}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        aria-label="Attach a photo or video"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-night/60 transition-colors hover:bg-night/5 disabled:opacity-40"
      >
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
          <path
            d="M4 8a2 2 0 0 1 2-2h1.5l.9-1.5A1.5 1.5 0 0 1 9.7 4h4.6a1.5 1.5 0 0 1 1.3.75L16.5 6H18a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <circle cx="12" cy="12.5" r="3" stroke="currentColor" strokeWidth="1.6" />
        </svg>
      </button>
    </>
  );
}
