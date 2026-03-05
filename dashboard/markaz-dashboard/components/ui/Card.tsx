import React from "react";

export interface CardProps {
    children: React.ReactNode;
    style?: React.CSSProperties;
    className?: string;
}

export default function Card({ children, style, className = "" }: CardProps): React.JSX.Element {
    return (
        <div className={`card ${className}`.trim()} style={style}>
            {children}
        </div>
    );
}
