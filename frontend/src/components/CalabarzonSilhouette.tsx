interface Props {
  className?: string;
}

// Stylized silhouette of CALABARZON provinces (approximate, not geographically precise).
export function CalabarzonSilhouette({ className }: Props) {
  return (
    <svg
      viewBox="0 0 800 600"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <g className="silhouette-pulse">
        {/* Rizal */}
        <path d="M310 180 L380 165 L430 195 L420 235 L370 250 L320 230 Z" />
        {/* Cavite */}
        <path d="M210 270 L295 255 L320 290 L290 340 L230 340 L200 305 Z" />
        {/* Laguna */}
        <path d="M310 280 L420 270 L460 320 L420 360 L340 355 L305 320 Z" />
        {/* Batangas */}
        <path d="M210 360 L320 360 L380 380 L370 460 L290 490 L210 460 L180 410 Z" />
        {/* Quezon (long curved) */}
        <path d="M430 250 L540 240 L640 280 L700 340 L660 380 L580 360 L520 340 L460 320 Z" />
        <path d="M650 380 L720 410 L740 450 L700 470 L640 450 Z" />
      </g>
    </svg>
  );
}
