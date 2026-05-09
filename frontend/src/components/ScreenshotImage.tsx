import { Maximize2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { resolveScreenshotUrl } from "../lib/api";

type ScreenshotImageProps = {
  src: string;
  alt: string;
};

export function ScreenshotImage({ src, alt }: ScreenshotImageProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [retryToken, setRetryToken] = useState(0);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const resolvedSrc = resolveScreenshotUrl(src);
  const cacheBustedSrc = retryToken > 0 ? `${resolvedSrc}${resolvedSrc.includes("?") ? "&" : "?"}r=${retryToken}` : resolvedSrc;

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setIsOpen(false);
      }
    }
    window.addEventListener("keydown", handleKey);

    return () => {
      window.removeEventListener("keydown", handleKey);
      if (previouslyFocused && typeof previouslyFocused.focus === "function") {
        previouslyFocused.focus();
      } else {
        triggerRef.current?.focus();
      }
    };
  }, [isOpen]);

  if (hasError) {
    return (
      <div className="screenshot-fallback" role="img" aria-label={alt}>
        <span>Screenshot unavailable</span>
        <button
          type="button"
          onClick={() => {
            setHasError(false);
            setRetryToken((token) => token + 1);
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <>
      <button
        ref={triggerRef}
        className="screenshot-button"
        type="button"
        onClick={() => setIsOpen(true)}
        aria-label={`Expand ${alt}`}
      >
        <img src={cacheBustedSrc} alt={alt} loading="lazy" onError={() => setHasError(true)} />
        <span aria-hidden="true">
          <Maximize2 size={16} />
        </span>
      </button>
      {isOpen ? (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label={alt}
          onClick={() => setIsOpen(false)}
        >
          <button
            ref={closeRef}
            className="modal-image"
            type="button"
            onClick={() => setIsOpen(false)}
            aria-label="Close screenshot"
          >
            <img src={cacheBustedSrc} alt={alt} />
          </button>
        </div>
      ) : null}
    </>
  );
}
