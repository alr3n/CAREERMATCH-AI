export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-bold text-ink ${className}`}>
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="#0F6E66" />
        <rect x="6" y="19" width="9" height="5" rx="1.5" fill="#E2F0EC" />
        <rect x="15" y="19" width="6" height="5" rx="1.5" fill="#A9D3CB" />
        <rect x="21" y="19" width="5" height="5" rx="1.5" fill="#6BB3A6" opacity=".6" />
        <path d="M8 13.5l3.2 3 6.8-7.5" stroke="#fff" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      CareerMatch AI
    </span>
  );
}
