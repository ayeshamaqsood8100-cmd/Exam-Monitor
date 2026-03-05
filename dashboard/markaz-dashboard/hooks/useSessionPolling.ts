"use client";
import { useState, useEffect } from "react";
import { type SessionWithStudent } from "@/lib/sessions";
export function useSessionPolling(
    examId: string,
    initialSessions: SessionWithStudent[],
    intervalMs: number = 30000
) {
    const [sessions, setSessions] = useState<SessionWithStudent[]>(initialSessions);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
    useEffect(() => {
        if (!examId) return;
        let isMounted = true;
        const fetchSessions = async () => {
            if (!isMounted) return;
            setIsRefreshing(true);
            try {
                const res = await fetch(`/api/sessions?exam_id=${examId}`);
                if (!res.ok) throw new Error(`API returned ${res.status}`);
                const data: SessionWithStudent[] = await res.json();
                if (isMounted) {
                    setSessions(data);
                    setLastRefreshed(new Date());
                }
            } catch (err) {
                console.warn("Failed to poll sessions:", err);
            } finally {
                if (isMounted) setIsRefreshing(false);
            }
        };
        const intervalId = setInterval(fetchSessions, intervalMs);
        return () => {
            isMounted = false;
            clearInterval(intervalId);
        };
    }, [examId, intervalMs]);
    return { sessions, isRefreshing, lastRefreshed };
}
