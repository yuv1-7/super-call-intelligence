import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket.js';
import { useDeepgramSpeech } from '../hooks/useSpeechRecognition.js';

const CallContext = createContext(null);

export function useCall() {
    return useContext(CallContext);
}

export function CallProvider({ children }) {
    const { userId } = useAuth();
    const navigate = useNavigate();
    const [callActive, setCallActive] = useState(false);
    const [showEvaluation, setShowEvaluation] = useState(false);
    const [postCallTab, setPostCallTab] = useState(0);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const WS_URL = import.meta.env.DEV
        ? `ws://${window.location.hostname}:8000/stream`
        : `${protocol}//${window.location.host}/stream`;

    const wsProps = useWebSocket(WS_URL);

    useEffect(() => {
        if (wsProps.isConnected && userId && wsProps.sendRawMessage) {
            wsProps.sendRawMessage({ type: 'auth', clerk_user_id: userId });
        }
    }, [wsProps.isConnected, userId, wsProps.sendRawMessage]);

    const onTranscript = useCallback(
        (event) => {
            const speakerLabel = event.speaker === '0' ? 'Agent' : event.speaker === '1' ? 'Customer' : `Speaker ${event.speaker}`;
            const offset = event.offset || 0;
            const h = Math.floor(offset / 3600);
            const m = Math.floor((offset % 3600) / 60);
            const s = Math.floor(offset % 60);
            const timestamp = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

            wsProps.addTranscript({
                text: event.text,
                is_finalized: event.isFinal,
                speaker: speakerLabel,
                timestamp,
                offset,
            });

            wsProps.sendMessage(event.text, event.isFinal, event.speaker, event.offset, event.languages || []);
        },
        [wsProps.sendMessage, wsProps.addTranscript]
    );

    const speech = useDeepgramSpeech({ onTranscript });

    const handleStartCall = () => {
        wsProps.resetState();
        setCallActive(true);
        setShowEvaluation(false);
        navigate('/call');
        setTimeout(() => speech.toggleListening(), 300);
    };

    const handleEndCall = () => {
        if (speech.isListening) speech.toggleListening();
        wsProps.endCall();
        setCallActive(false);
        setShowEvaluation(true);
    };

    const handleNewCall = () => {
        wsProps.resetState();
        setCallActive(false);
        setShowEvaluation(false);
        setPostCallTab(0);
    };

    const value = {
        ...wsProps,
        ...speech,
        callActive, setCallActive,
        showEvaluation, setShowEvaluation,
        postCallTab, setPostCallTab,
        handleStartCall, handleEndCall, handleNewCall
    };

    return <CallContext.Provider value={value}>{children}</CallContext.Provider>;
}
