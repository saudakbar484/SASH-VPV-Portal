export function PalmWireframeOverlay({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 120 160"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="M60 20 C45 20 38 35 38 50 L38 90 C38 110 48 125 60 130 C72 125 82 110 82 90 L82 50 C82 35 75 20 60 20Z"
        stroke="var(--primary)"
        strokeWidth="1.2"
        opacity="0.5"
      />
      <path d="M60 55 L60 95" stroke="var(--primary)" strokeWidth="1" opacity="0.7" />
      <path d="M50 70 L70 70 M48 85 L72 85 M52 100 L68 100" stroke="var(--primary)" strokeWidth="0.8" opacity="0.5" />
      <circle cx="60" cy="65" r="3" fill="var(--primary)" opacity="0.8" />
      <circle cx="50" cy="45" r="2" fill="var(--primary)" opacity="0.6" />
      <circle cx="70" cy="45" r="2" fill="var(--primary)" opacity="0.6" />
    </svg>
  )
}
