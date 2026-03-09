"use client";
import React from "react";
import Link from "next/link";
import { THEME } from "@/constants/theme";
export default function NavLinks(): React.JSX.Element {
    return (
        <div style={{ display: "flex", gap: "24px", marginLeft: "auto" }}>
            <Link href="/exams" style={{ color: THEME.textSecondary, textDecoration: "none", fontSize: "14px", fontWeight: 500, transition: "color 0.2s" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = THEME.cyan)}
                onMouseLeave={(e) => (e.currentTarget.style.color = THEME.textSecondary)}>
                Exams
            </Link>
            <Link href="/flagged" style={{ color: THEME.textSecondary, textDecoration: "none", fontSize: "14px", fontWeight: 500, transition: "color 0.2s" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = THEME.cyan)}
                onMouseLeave={(e) => (e.currentTarget.style.color = THEME.textSecondary)}>
                Flagged Events
            </Link>
            <Link href="/alerts" style={{ color: THEME.textSecondary, textDecoration: "none", fontSize: "14px", fontWeight: 500, transition: "color 0.2s" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = THEME.cyan)}
                onMouseLeave={(e) => (e.currentTarget.style.color = THEME.textSecondary)}>
                Alerts
            </Link>
        </div>
    );
}
