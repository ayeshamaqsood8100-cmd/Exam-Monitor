import React from "react";
import Skeleton from "@/components/ui/Skeleton";

export default function ExamsLoading(): React.JSX.Element {
    return (
        <div style={{
            maxWidth: "1200px",
            margin: "0 auto",
            padding: "36px 24px",
            display: "flex",
            flexDirection: "column",
            gap: "20px"
        }}>
            {/* Heading Block */}
            <Skeleton width="200px" height="28px" />

            {/* Buttons Row */}
            <div style={{ display: "flex", gap: "16px", marginBottom: "12px" }}>
                <Skeleton width="120px" height="36px" />
                <Skeleton width="120px" height="36px" />
            </div>

            {/* Grid of Exam Cards */}
            <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                gap: "24px"
            }}>
                <Skeleton height="120px" />
                <Skeleton height="120px" />
                <Skeleton height="120px" />
                <Skeleton height="120px" />
                <Skeleton height="120px" />
                <Skeleton height="120px" />
            </div>
        </div>
    );
}
