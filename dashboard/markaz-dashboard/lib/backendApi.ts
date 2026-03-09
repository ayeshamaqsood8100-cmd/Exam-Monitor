// SERVER ONLY

interface BackendErrorPayload {
    detail?: string;
    error?: string;
}

export class BackendRequestError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.name = "BackendRequestError";
        this.status = status;
    }
}

function getBackendConfig(): { backendUrl: string; backendApiKey: string } {
    const backendUrl = process.env.BACKEND_URL;
    const backendApiKey = process.env.BACKEND_API_KEY;

    if (!backendUrl || !backendApiKey) {
        throw new Error("Missing BACKEND_URL or BACKEND_API_KEY in process.env");
    }

    return {
        backendUrl: backendUrl.replace(/\/$/, ""),
        backendApiKey,
    };
}

export async function postToBackend<TResponse>(
    path: string,
    body?: unknown,
): Promise<TResponse> {
    const { backendUrl, backendApiKey } = getBackendConfig();
    const response = await fetch(`${backendUrl}${path}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-API-Key": backendApiKey,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
    });

    const raw = await response.text();
    const payload = raw ? JSON.parse(raw) as TResponse | BackendErrorPayload : null;

    if (!response.ok) {
        const errorPayload = payload as BackendErrorPayload | null;
        throw new BackendRequestError(
            errorPayload?.detail || errorPayload?.error || `Backend request failed with status ${response.status}`,
            response.status,
        );
    }

    return payload as TResponse;
}
