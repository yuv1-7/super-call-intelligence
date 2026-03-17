// hooks/useApi.js — API client with Clerk auth headers

import { useAuth } from '@clerk/clerk-react';
import { useCallback } from 'react';

export function useApi() {
    const { getToken } = useAuth();

    const fetchWithAuth = useCallback(async (url, options = {}) => {
        const token = await getToken();
        const res = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...options.headers,
            },
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || res.statusText);
        }
        return res.json();
    }, [getToken]);

    return { fetchWithAuth };
}
