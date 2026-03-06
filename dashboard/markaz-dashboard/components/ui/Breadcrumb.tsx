"use client";

import React, { useState } from "react";
import Link from "next/link";
import { THEME } from "@/constants/theme";

export interface BreadcrumbSegment {
    label: string;
    href?: string;
}

export interface BreadcrumbProps {
    segments: BreadcrumbSegment[];
}

function BreadcrumbLink({ segment }: { segment: BreadcrumbSegment }): React.JSX.Element {
    const [isHovered, setIsHovered] = useState(false);
    return (
        <Link
            href={segment.href!}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            style={{
                color: THEME.cyan,
                textDecoration: isHovered ? "underline" : "none",
                transition: "all 0.2s"
            }}
        >
            {segment.label}
        </Link>
    );
}

export default function Breadcrumb({ segments }: BreadcrumbProps): React.JSX.Element {
    return (
        <div style={{ display: "flex", alignItems: "center", marginBottom: "28px", fontSize: "13px", fontFamily: THEME.fontSans }}>
            {segments.map((segment, index) => {
                const isLast = index === segments.length - 1;

                return (
                    <React.Fragment key={index}>
                        {segment.href ? (
                            <BreadcrumbLink segment={segment} />
                        ) : (
                            <span style={{ color: THEME.textSecondary }}>
                                {segment.label}
                            </span>
                        )}
                        {!isLast && (
                            <span style={{ color: "rgba(255,255,255,0.15)", margin: "0 8px" }}>
                                /
                            </span>
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}
