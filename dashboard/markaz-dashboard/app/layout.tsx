import React from "react";
import NavLinks from "@/components/ui/NavLinks";
import "@/styles/globals.css";

export const metadata = {
    title: "Markaz Exam Monitor",
    description: "Consent-based desktop monitoring agent dashboard",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}): React.JSX.Element {
    return (
        <html lang="en">
            <body>
                <div className="aesthetic-bg-glow" />

                {/* Global Navigation */}
                <nav className="glass-nav">
                    {/* Logo Section */}
                    <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--accent-purple)] to-[var(--accent-cyan)] flex items-center justify-center text-white font-bold text-sm shadow-[0_2px_10px_rgba(139,92,246,0.3)]">
                            M
                        </div>
                        <span className="text-[var(--text-primary)] font-semibold text-base tracking-[-0.02em]">
                            Markaz
                        </span>
                    </div>

                    {/* Links Section */}
                    <NavLinks />
                </nav>

                {/* Main Content Area */}
                <main className="max-w-[1100px] mx-auto pt-10 px-10 pb-12 relative z-0">
                    {children}
                </main>
            </body>
        </html>
    );
}
