import React from "react";
import NavLinks from "@/components/ui/NavLinks";
import "@/styles/globals.css";
import { THEME } from "@/constants/theme";

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
        <html lang="en" style={{ background: THEME.bg }}>
            <body>
                {/* Ambient Glows (z-index 0) */}
                <div
                    style={{
                        position: "fixed",
                        top: 0,
                        right: 0,
                        width: "600px",
                        height: "600px",
                        background: "radial-gradient(circle, rgba(0,245,212,0.04) 0%, transparent 70%)",
                        pointerEvents: "none",
                        zIndex: 0
                    }}
                />
                <div
                    style={{
                        position: "fixed",
                        bottom: 0,
                        left: 0,
                        width: "500px",
                        height: "500px",
                        background: "radial-gradient(circle, rgba(114,9,183,0.05) 0%, transparent 70%)",
                        pointerEvents: "none",
                        zIndex: 0
                    }}
                />

                {/* Global Navigation */}
                <nav
                    style={{
                        position: "fixed",
                        top: 0,
                        left: 0,
                        right: 0,
                        height: "64px",
                        background: "rgba(8,12,20,0.8)",
                        backdropFilter: "blur(12px)",
                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                        zIndex: 50,
                        display: "flex",
                        alignItems: "center",
                        padding: "0 24px"
                    }}
                >
                    {/* Logo Section */}
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <div
                            style={{
                                width: "32px",
                                height: "32px",
                                borderRadius: "8px",
                                background: `linear-gradient(135deg, ${THEME.pink}, ${THEME.purple})`,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: THEME.textPrimary,
                                fontWeight: "bold",
                                fontSize: "18px"
                            }}
                        >
                            M
                        </div>
                        <span style={{ color: THEME.textPrimary, fontWeight: 600, fontSize: "18px", letterSpacing: "0.5px" }}>
                            Markaz
                        </span>
                    </div>

                    {/* Links Section */}
                    <NavLinks />
                </nav>

                {/* Main Content Area */}
                <main
                    style={{
                        maxWidth: "1100px",
                        margin: "0 auto",
                        padding: "100px 24px 48px",
                        position: "relative",
                        zIndex: 1
                    }}
                >
                    {children}
                </main>
            </body>
        </html>
    );
}
