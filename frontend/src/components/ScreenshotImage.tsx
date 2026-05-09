import { Maximize2 } from "lucide-react";
import { useState } from "react";
import { resolveScreenshotUrl } from "../lib/api";

type ScreenshotImageProps = {
  src: string;
  alt: string;
};

export function ScreenshotImage({ src, alt }: ScreenshotImageProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hasError, setHasError] = useState(false);
  const resolvedSrc = resolveScreenshotUrl(src);

  if (hasError) {
    return (
      <div className="screenshot-fallback" role="img" aria-label={alt}>
        Screenshot unavailable
      </div>
    );
  }

  return (
    <>
      <button className="screenshot-button" type="button" onClick={() => setIsOpen(true)}>
        <img src={resolvedSrc} alt={alt} loading="lazy" onError={() => setHasError(true)} />
        <span>
          <Maximize2 size={16} />
        </span>
      </button>
      {isOpen ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={() => setIsOpen(false)}>
          <button className="modal-image" type="button" onClick={() => setIsOpen(false)}>
            <img src={resolvedSrc} alt={alt} />
          </button>
        </div>
      ) : null}
    </>
  );
}
