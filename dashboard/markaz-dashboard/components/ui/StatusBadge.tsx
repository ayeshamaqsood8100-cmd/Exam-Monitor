import React from "react";
import { THEME } from "@/constants/theme";

export interface StatusBadgeProps {
    label: string;
    variant: "HIGH" | "MED" | "LOW" | "active" | "completed" | "idle";
}

export default function StatusBadge({ label, variant }: StatusBadgeProps): React.JSX.Element {
    let color = THEME.textMuted;

    switch (variant) {
        case "HIGH":
            color = THEME.pink;
            break;
        case "MED":
            color = THEME.yellow;
            break;
        case "LOW":
            color = THEME.cyan;
            break;
        case "active":
            color = THEME.cyan;
            break;
        case "completed":
            color = THEME.purple;
            break;
        case "idle":
        default:
            color = THEME.textSecondary;
            break;
    }

    return (
        <span
            style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "4px 10px",
                borderRadius: "9999px",
                fontSize: "12px",
                fontWeight: 600,
                backgroundColor: `${color}1A`, // 10% opacity hex shorthand
                color: color,
                border: `1px solid ${color}33` // 20% opacity hex shorthand
            }}
        >
            {label}
        </span>
    );
}
