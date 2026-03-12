import React from "react";
import Link from "next/link";

interface BackButtonProps {
    href: string;
    breadcrumbs: string[];
}

export default function BackButton({ href, breadcrumbs }: BackButtonProps): React.JSX.Element {
    return (
        <div className="flex items-center gap-4 mb-6">
            <Link 
                href={href} 
                className="flex items-center justify-center w-9 h-9 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] hover:border-[var(--border-hover)] transition-all duration-200"
                title="Go Back"
            >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                </svg>
            </Link>
            <div className="text-[13px] text-[var(--text-secondary)] flex items-center gap-2">
                {breadcrumbs.map((crumb, idx) => (
                    <React.Fragment key={idx}>
                        {idx > 0 && <span>/</span>}
                        <span className={idx === breadcrumbs.length - 1 ? "text-[var(--text-primary)] font-medium" : ""}>
                            {crumb}
                        </span>
                    </React.Fragment>
                ))}
            </div>
        </div>
    );
}
