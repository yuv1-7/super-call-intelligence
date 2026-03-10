import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Custom hook for WebSocket connection to the FastAPI backend.
 * Handles connection, reconnection, sending messages, and routing incoming data.
 * Supports speaker-labeled transcripts and post-call evaluation.
 */
export function useWebSocket(url) {
    const [isConnected, setIsConnected] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);

    // State for each UI card
    const [transcripts, setTranscripts] = useState([]);
    const [memberProfile, setMemberProfile] = useState(null);
    const [knowledgeDocs, setKnowledgeDocs] = useState([]);
    const [complianceAlerts, setComplianceAlerts] = useState([]);
    const [suggestion, setSuggestion] = useState('');
    const [intent, setIntent] = useState(null);
    const [postCallEvaluation, setPostCallEvaluation] = useState(null);

    const wsRef = useRef(null);
    const reconnectTimerRef = useRef(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(url);

        ws.onopen = () => {
            setIsConnected(true);
            console.log('🔌 WebSocket connected');
        };

        ws.onclose = () => {
            setIsConnected(false);
            console.log('🔌 WebSocket disconnected, reconnecting in 3s...');
            reconnectTimerRef.current = setTimeout(connect, 3000);
        };

        ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleMessage(msg);
            } catch (e) {
                console.error('Failed to parse WS message:', e);
            }
        };

        wsRef.current = ws;
    }, [url]);

    const handleMessage = useCallback((msg) => {
        const { type, data } = msg;

        switch (type) {
            case 'transcript':
                setTranscripts((prev) => {
                    // Helper: check if two texts are substantially similar (>50% word overlap)
                    const isSimilar = (a, b) => {
                        const wa = new Set(a.toLowerCase().split(/\s+/));
                        const wb = new Set(b.toLowerCase().split(/\s+/));
                        const overlap = [...wa].filter(w => wb.has(w)).length;
                        return overlap / Math.max(wa.size, wb.size, 1) > 0.5;
                    };

                    if (data.is_finalized) {
                        // Remove: (a) exact offset partials AND (b) nearby partials with similar text
                        // This handles multichannel bleed where same speech appears on both channels
                        const filtered = prev.filter((t) => {
                            if (t.is_finalized) return true; // keep all finals
                            // Remove partials with same offset
                            if (t.offset === data.offset) return false;
                            // Remove partials within 2s time window with similar text (cross-channel bleed)
                            if (Math.abs(t.offset - data.offset) < 2 && isSimilar(t.text, data.text)) return false;
                            return true;
                        });
                        return [...filtered, {
                            text: data.text,
                            is_finalized: true,
                            speaker: data.speaker || '',
                            timestamp: data.timestamp || '',
                            offset: data.offset,
                            languages: data.languages || [],
                            id: Date.now(),
                        }];
                    }
                    // For partials: replace existing partial at same offset
                    const filteredPartial = prev.filter((t) => t.is_finalized || t.offset !== data.offset);
                    return [...filteredPartial, {
                        text: data.text,
                        is_finalized: false,
                        speaker: data.speaker || '',
                        timestamp: data.timestamp || '',
                        offset: data.offset,
                        languages: data.languages || [],
                        id: Date.now(),
                    }];
                });
                break;

            case 'member_profile':
                setMemberProfile(data);
                break;

            case 'knowledge':
                setKnowledgeDocs(data);
                break;

            case 'compliance':
                setComplianceAlerts(data);
                break;

            case 'suggestion':
                setSuggestion(data.text);
                setIsProcessing(false);
                break;

            case 'suggestion_chunk':
                // Append chunk to existing suggestion
                setSuggestion((prev) => prev + data.text);
                setIsProcessing(false);
                break;

            case 'clear_suggestion':
                setSuggestion('');
                break;

            case 'intent':
                setIntent(data);
                setIsProcessing(false);
                break;

            case 'processing':
                setIsProcessing(true);
                // We no longer clear the suggestion here. We only clear it if we want to explicitly reset.
                // Otherwise, rapid speech will cause the UI to flash empty.
                break;

            case 'post_call_evaluation':
                setPostCallEvaluation(data);
                setIsProcessing(false);
                break;

            case 'error':
                console.error('Server error:', data.message);
                setIsProcessing(false);
                break;

            default:
                console.warn('Unknown message type:', type);
        }
    }, []);

    const sendMessage = useCallback((text, isFinalized = true, speaker = 'Unknown', offset = 0, languages = []) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                text,
                is_finalized: isFinalized,
                speaker,
                offset,
                languages,
            }));
        }
    }, []);

    const endCall = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'end_call' }));
        }
    }, []);

    const resetState = useCallback(() => {
        setTranscripts([]);
        setMemberProfile(null);
        setKnowledgeDocs([]);
        setComplianceAlerts([]);
        setSuggestion('');
        setIntent(null);
        setIsProcessing(false);
        setPostCallEvaluation(null);
        // Also reset backend state
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'new_call' }));
        }
    }, []);

    useEffect(() => {
        connect();
        return () => {
            clearTimeout(reconnectTimerRef.current);
            wsRef.current?.close();
        };
    }, [connect]);

    return {
        isConnected,
        isProcessing,
        transcripts,
        memberProfile,
        knowledgeDocs,
        complianceAlerts,
        suggestion,
        intent,
        postCallEvaluation,
        sendMessage,
        endCall,
        resetState,
    };
}
