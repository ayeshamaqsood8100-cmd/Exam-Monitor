import React from "react";
import Skeleton from "@/components/ui/Skeleton";

export default function SessionsLoading(): React.JSX.Element {
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
            <Skeleton width="220px" height="14px" />

            {/* Heading Block */}
            <Skeleton width="260px" height="28px" />

            {/* Table layout (list of rows) */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "16px" }}>
                <Skeleton height="52px" />
                <Skeleton height="52px" />
                <Skeleton height="52px" />
                <Skeleton height="52px" />
                <Skeleton height="52px" />
            </div>
        </div>
    );
}
