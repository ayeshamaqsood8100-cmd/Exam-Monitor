import React from "react";
import Skeleton from "@/components/ui/Skeleton";

export default function SessionSummaryLoading(): React.JSX.Element {
    return (
        <div style={{
            maxWidth: "1200px",
            margin: "0 auto",
            padding: "36px 24px",
            display: "flex",
            flexDirection: "column",
            gap: "20px"
        }}>
            {/* Breadcrumb Skeleton */}
            <Skeleton width="300px" height="14px" />

            {/* Heading Block */}
            <Skeleton width="320px" height="28px" />

            {/* Stat Cards Row */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px", marginTop: "12px" }}>
                <Skeleton height="80px" />
                <Skeleton height="80px" />
                <Skeleton height="80px" />
            </div>

            {/* Tab Bar Skeleton */}
            <Skeleton width="360px" height="36px" style={{ marginTop: "16px" }} />

            {/* Large Content Block */}
            <Skeleton height="300px" style={{ marginTop: "8px" }} />
        </div>
    );
}
