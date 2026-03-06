"use client";

import React from "react";

export interface SkeletonProps {
    width?: string;
    height?: string;
    borderRadius?: string;
    style?: React.CSSProperties;
}

export default function Skeleton({
    width = "100%",
    height = "16px",
    borderRadius = "8px",
    style
}: SkeletonProps): React.JSX.Element {
    return (
        <>
            <style dangerouslySetInnerHTML={{
                __html: `
                    @keyframes shimmer {
                        0% { background-position: -1000px 0; }
                        100% { background-position: 1000px 0; }
                    }
                `
            }} />
            <div
                style={{
                    width,
                    height,
                    borderRadius,
                    background: "linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)",
                    backgroundSize: "1000px 100%",
                    animation: "shimmer 2s infinite linear",
                    ...style
                }}
            />
        </>
    );
}
