// The frame around every page: font, header with menu, footer with name and links
import type { Metadata } from "next";
import Link from "next/link";
import "@fontsource-variable/inter";
import "./globals.css";
import Nav from "@/components/Nav";
import meta from "@/public/data/meta.json";

export const metadata: Metadata = {
  title: "RBI/SEBI Regulation Copilot",
  description: "Ask questions about RBI and SEBI rules and get answers from the official documents, with page citations.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="site-name"><span className="site-mark" aria-hidden="true">§</span>Regulation Copilot</Link>
            <Nav />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="site-footer">
          <div className="wrap footer-row">
            <p className="footer-by">Built by <strong>Aditya Khetarpal</strong></p>
            <nav className="footer-links" aria-label="Aditya Khetarpal elsewhere">
              <a href="https://github.com/AdityaKhetarpal" target="_blank" rel="noreferrer">GitHub</a>
              <a href="https://www.linkedin.com/in/adityakhetarpal" target="_blank" rel="noreferrer">LinkedIn</a>
              <a href="https://github.com/AdityaKhetarpal/rbi-sebi-regulation-copilot" target="_blank" rel="noreferrer">Source code</a>
            </nav>
          </div>
          <div className="wrap">
            <p className="footer-note">
              Answers come only from official RBI/SEBI documents{meta.built_on ? `, indexed on ${meta.built_on}` : ""}. Information, not legal advice. Always check the original circular.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
