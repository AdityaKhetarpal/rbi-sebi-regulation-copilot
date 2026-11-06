// The site logo. Plain shapes, so it needs no font and stays sharp at any size.
// The [1] citation marker: the answer sits inside the brackets or it doesn't get said.
export default function SiteMark() {
  return (
    <span className="site-mark" aria-hidden="true">
      <svg viewBox="2 2 28 28">
        <path d="M4.4 3.8H15L10.4 8.4H9.4V23.6H15L10.4 28.2H4.4Z" fill="var(--mark)" stroke="var(--mark)" strokeWidth="0.8" strokeLinejoin="round" />
        <path d="M27.6 3.8H21.6L17 8.4H22.6V23.6H21.6L17 28.2H27.6Z" fill="var(--mark)" stroke="var(--mark)" strokeWidth="0.8" strokeLinejoin="round" />
        <circle cx="16" cy="16" r="4.3" fill="var(--accent-2)" />
      </svg>
    </span>
  );
}
