import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket.js';
import { useDeepgramSpeech } from '../hooks/useSpeechRecognition.js';
import { onSuggestionComplete } from '../hooks/useWebSocket.js';

const CallContext = createContext(null);

export function useCall() {
    return useContext(CallContext);
}

// ── Deepgram TTS Helper ──
// Calls Deepgram REST TTS API and returns an audio blob URL
async function synthesizeSpeech(text, apiKey) {
    const res = await fetch('https://api.deepgram.com/v1/speak?model=aura-asteria-en&encoding=mp3', {
        method: 'POST',
        headers: {
            'Authorization': `Token ${apiKey}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
    });
    if (!res.ok) {
        throw new Error(`Deepgram TTS failed: ${res.status} ${res.statusText}`);
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
}

export function CallProvider({ children }) {
    const { userId } = useAuth();
    const navigate = useNavigate();
    const [callActive, setCallActive] = useState(false);
    const [showEvaluation, setShowEvaluation] = useState(false);
    const [postCallTab, setPostCallTab] = useState(0);
    const [callElapsed, setCallElapsed] = useState(0);
    const callTimerRef = useRef(null);

    // ── AI Auto-Speak State ──
    const [aiEnabled, setAiEnabled] = useState(false);
    const [aiSpeaking, setAiSpeaking] = useState(false);
    const aiEnabledRef = useRef(false);
    const audioRef = useRef(null);          // Current playing Audio element
    const dgKeyRef = useRef(null);          // Cached Deepgram API key
    const greetingTimerRef = useRef(null);  // 2-second greeting timer
    const greetingSentRef = useRef(false);  // Whether we already sent the greeting
    const customerSpokeRef = useRef(false); // Whether customer has spoken yet
    const ttsQueueRef = useRef([]);         // Queue of texts to speak
    const isSpeakingRef = useRef(false);    // Whether we're currently speaking (ref for async)
    const lastSpokenTextRef = useRef('');   // Last text that was spoken (for deduplication)

    // Keep ref in sync with state
    useEffect(() => {
        aiEnabledRef.current = aiEnabled;
    }, [aiEnabled]);

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

    // ── Fetch and cache Deepgram key ──
    const ensureDgKey = useCallback(async () => {
        if (dgKeyRef.current) return dgKeyRef.current;
        const baseUrl = import.meta.env.DEV
            ? `http://${window.location.hostname}:8000`
            : '';
        const res = await fetch(`${baseUrl}/api/deepgram-token`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        dgKeyRef.current = data.token;
        return data.token;
    }, []);

    const lastAiSpeechEndTimeRef = useRef(0);
    const recentlySpokenRef = useRef([]);

    // ── Deepgram TTS Helper ──
    const speakText = useCallback(async (text) => {
        if (!text || !text.trim()) return;

        // Strip markdown-style formatting for cleaner speech
        const cleanText = text
            .replace(/[─═*#_><]/g, '')
            .replace(/\n{2,}/g, '. ')
            .replace(/\n/g, ' ')
            .trim();

        if (!cleanText) return;

        try {
            const key = await ensureDgKey();
            const audioUrl = await synthesizeSpeech(cleanText, key);
            
            // If AI was disabled while we were fetching, bail
            if (!aiEnabledRef.current) {
                URL.revokeObjectURL(audioUrl);
                return;
            }

            const audio = new Audio(audioUrl);
            audioRef.current = audio;
            setAiSpeaking(true);
            isSpeakingRef.current = true;
            
            recentlySpokenRef.current.push(cleanText.toLowerCase().replace(/[^a-z0-9 ]/g, ''));
            if (recentlySpokenRef.current.length > 5) {
                recentlySpokenRef.current.shift();
            }

            await new Promise((resolve, reject) => {
                audio.onended = resolve;
                audio.onerror = reject;
                audio.play().catch(reject);
            });

            URL.revokeObjectURL(audioUrl);
        } catch (err) {
            console.error('TTS error:', err);
        } finally {
            setAiSpeaking(false);
            isSpeakingRef.current = false;
            lastAiSpeechEndTimeRef.current = Date.now();
            audioRef.current = null;
        }
    }, [ensureDgKey]);

    // ── Queue-based TTS: process texts one at a time ──
    const processTtsQueue = useCallback(async () => {
        if (isSpeakingRef.current) return; // Already speaking, will get called again
        
        while (ttsQueueRef.current.length > 0 && aiEnabledRef.current) {
            const text = ttsQueueRef.current.shift();
            await speakText(text);
        }
    }, [speakText]);

    const queueSpeak = useCallback((text) => {
        if (!aiEnabledRef.current) return;
        ttsQueueRef.current.push(text);
        processTtsQueue();
    }, [processTtsQueue]);

    // ── Stop all TTS playback ──
    const stopSpeaking = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
            audioRef.current = null;
        }
        ttsQueueRef.current = [];
        setAiSpeaking(false);
        isSpeakingRef.current = false;
        lastAiSpeechEndTimeRef.current = Date.now();
    }, []);

    // ── Subscribe to suggestion completions for auto-speak ──
    useEffect(() => {
        const unsub = onSuggestionComplete((text) => {
            if (!aiEnabledRef.current) return;

            // Strip decorative separators and whitespace
            const clean = text.replace(/[─═\s]/g, '').trim();
            if (!clean) return;

            // Deduplicate: don't speak the exact same text back-to-back
            const normalized = clean.toLowerCase().replace(/[^a-z0-9 ]/g, '');
            if (normalized === lastSpokenTextRef.current) {
                console.log('🤖 AI Auto-Speak: skipping duplicate suggestion');
                return;
            }
            lastSpokenTextRef.current = normalized;

            // Stop any currently playing speech and clear queue before queuing new
            stopSpeaking();

            console.log('🤖 AI Auto-Speak: queuing suggestion TTS');
            queueSpeak(text);
        });
        return unsub;
    }, [queueSpeak, stopSpeaking]);

    const onTranscript = useCallback(
        (event) => {
            // Fallback STT latency hook + explicit text match to override AI audio picked up by mic
            const timeSinceAiSpoke = Date.now() - lastAiSpeechEndTimeRef.current;
            let isAiEcho = false;
            
            if (event.speaker === '1' && event.text?.trim()) {
                const normText = event.text.toLowerCase().replace(/[^a-z0-9 ]/g, '');
                for (const spoken of recentlySpokenRef.current) {
                    if (spoken.includes(normText) || normText.includes(spoken) || spoken.length > 10 && normText.length > 10 && (spoken.startsWith(normText.substring(0, 10)) || normText.startsWith(spoken.substring(0, 10)))) {
                        isAiEcho = true;
                        break;
                    }
                }
            }

            if (event.speaker === '1' && (isSpeakingRef.current || timeSinceAiSpoke < 5000 || isAiEcho)) {
                event.speaker = '0';
            }

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

            // Track if customer has spoken (for greeting timer logic)
            // But only if it's TRULY the customer, not our AI tricking the STT
            if (speakerLabel === 'Customer' && event.isFinal) {
                customerSpokeRef.current = true;
                // Cancel the greeting timer if customer spoke first
                if (greetingTimerRef.current) {
                    clearTimeout(greetingTimerRef.current);
                    greetingTimerRef.current = null;
                    console.log('🤖 Customer spoke first — skipping AI greeting');
                }
            }
        },
        [wsProps.sendMessage, wsProps.addTranscript]
    );

    const speech = useDeepgramSpeech({ onTranscript });

    const handleStartCall = () => {
        wsProps.resetState();
        setCallActive(true);
        setShowEvaluation(false);
        setCallElapsed(0);
        callTimerRef.current = setInterval(() => setCallElapsed(t => t + 1), 1000);
        // Reset AI greeting state
        greetingSentRef.current = false;
        customerSpokeRef.current = false;
        navigate('/call');
        setTimeout(() => speech.toggleListening(), 300);

        // ── AI Greeting Timer ──
        // If AI is enabled, wait 2 seconds for customer to speak.
        // If they don't, speak the greeting.
        if (aiEnabledRef.current) {
            greetingTimerRef.current = setTimeout(() => {
                if (!customerSpokeRef.current && !greetingSentRef.current && aiEnabledRef.current) {
                    greetingSentRef.current = true;
                    console.log('🤖 AI Greeting: Customer hasn\'t spoken in 2s — sending greeting');
                    queueSpeak('Hi, how can I help you today?');
                }
            }, 2000);
        }
    };

    const handleEndCall = () => {
        if (speech.isListening) speech.toggleListening();
        wsProps.endCall();
        setCallActive(false);
        setShowEvaluation(true);
        clearInterval(callTimerRef.current);
        // Stop any AI speech
        stopSpeaking();
        if (greetingTimerRef.current) {
            clearTimeout(greetingTimerRef.current);
            greetingTimerRef.current = null;
        }
    };

    const handleNewCall = () => {
        wsProps.resetState();
        setCallActive(false);
        setShowEvaluation(false);
        setPostCallTab(0);
        setCallElapsed(0);
        clearInterval(callTimerRef.current);
        // Stop any AI speech
        stopSpeaking();
        greetingSentRef.current = false;
        customerSpokeRef.current = false;
        lastSpokenTextRef.current = '';
        if (greetingTimerRef.current) {
            clearTimeout(greetingTimerRef.current);
            greetingTimerRef.current = null;
        }
    };

    // ── Handle AI toggle during active call ──
    const handleToggleAi = useCallback(() => {
        const newState = !aiEnabledRef.current;
        setAiEnabled(newState);

        if (!newState) {
            // Turning off — stop everything
            stopSpeaking();
            if (greetingTimerRef.current) {
                clearTimeout(greetingTimerRef.current);
                greetingTimerRef.current = null;
            }
        } else if (callActive && !greetingSentRef.current && !customerSpokeRef.current) {
            // Turning on mid-call — start the greeting timer if customer hasn't spoken
            greetingTimerRef.current = setTimeout(() => {
                if (!customerSpokeRef.current && !greetingSentRef.current && aiEnabledRef.current) {
                    greetingSentRef.current = true;
                    console.log('🤖 AI Greeting: (toggled on mid-call) sending greeting');
                    queueSpeak('Hi, how can I help you today?');
                }
            }, 2000);
        }
    }, [callActive, stopSpeaking, queueSpeak]);

    const value = {
        ...wsProps,
        ...speech,
        callActive, setCallActive,
        showEvaluation, setShowEvaluation,
        postCallTab, setPostCallTab,
        callElapsed,
        handleStartCall, handleEndCall, handleNewCall,
        // AI Auto-Speak
        aiEnabled, aiSpeaking, handleToggleAi,
    };

    return <CallContext.Provider value={value}>{children}</CallContext.Provider>;
}
