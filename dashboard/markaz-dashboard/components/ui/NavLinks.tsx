"use client";
import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function NavLinks(): React.JSX.Element {
    const pathname = usePathname();

    const getLinkClass = (path: string) => {
        const isActive = pathname === path || pathname?.startsWith(`${path}/`);
        let baseClass = "text-sm font-medium transition-colors duration-200 relative ";
        
        if (isActive) {
            baseClass += "text-[var(--text-primary)] ";
            baseClass += "after:content-[''] after:absolute after:-bottom-[22px] after:left-0 after:w-full after:h-[2px] after:bg-[var(--accent-cyan)] after:rounded-t-sm after:shadow-[0_-2px_8px_rgba(6,182,212,0.4)]";
        } else {
            baseClass += "text-[var(--text-secondary)] hover:text-[var(--text-primary)]";
        }
        
        return baseClass;
    };

    return (
        <div className="flex gap-8 ml-12">
            <Link href="/exams" className={getLinkClass("/exams")}>
                Surveillance
            </Link>
            <Link href="/flagged" className={getLinkClass("/flagged")}>
                System Flags
            </Link>
            <Link href="/agent" className={getLinkClass("/agent")}>
                Agent Node Configuration
            </Link>
        </div>
    );
}
