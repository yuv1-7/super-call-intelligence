import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Custom hook for WebSocket connection to the FastAPI backend.
 * Handles connection, reconnection, sending messages, and routing incoming data.
 * Supports speaker-labeled transcripts and post-call evaluation.
 */
export function useWebSocket(url) {
    const [isConnected, setIsConnected] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [processingMessage, setProcessingMessage] = useState('');

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
                    if (data.is_finalized) {
                        // Remove matching partials by offset (not text!) to avoid duplicates
                        const filtered = prev.filter((t) => t.is_finalized || t.offset !== data.offset);
                        return [...filtered, {
                            text: data.text,
                            is_finalized: true,
                            speaker: data.speaker || '',
                            timestamp: data.timestamp || '',
                            offset: data.offset,
                            id: Date.now(),
                        }];
                    }
                    // Filter out existing partials for the SAME offset so we don't spam the UI
                    const filteredPartial = prev.filter((t) => t.is_finalized || t.offset !== data.offset);
                    return [...filteredPartial, {
                        text: data.text,
                        is_finalized: false,
                        speaker: data.speaker || '',
                        timestamp: data.timestamp || '',
                        offset: data.offset,
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
                setProcessingMessage('');
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
                // The new LangGraph stream triggers processing on EVERY tool invocation or reasoning loop.
                // We MUST clear the suggestion buffer when a new HumanMessage kicks off another ReAct loop, 
                // otherwise chunks will append to the old response.
                setSuggestion('');
                setProcessingMessage(data.message || 'Processing...');
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

    const sendRawMessage = useCallback((data) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(data));
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
        setProcessingMessage('');
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
        processingMessage,
        transcripts,
        memberProfile,
        knowledgeDocs,
        complianceAlerts,
        suggestion,
        intent,
        postCallEvaluation,
        sendMessage,
        sendRawMessage,
        endCall,
        resetState,
    };
}
