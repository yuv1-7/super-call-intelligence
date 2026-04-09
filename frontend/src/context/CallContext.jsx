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

// ── Language Detection Utility ──
// Detects whether text contains Hindi (Devanagari or Romanized) content.
// Returns "hi" for Hindi/mixed, "en" for pure English.
function detectLanguage(text) {
    if (!text) return 'en';

    // Check for Devanagari Unicode range (U+0900 – U+097F)
    const devanagariRegex = /[\u0900-\u097F]/;
    if (devanagariRegex.test(text)) return 'hi';

    // Common Romanized Hindi words/patterns (case-insensitive)
    // These are words that almost never appear in pure English context
    const hindiPatterns = [
        /\b(aap|aapka|aapki|aapke)\b/i,
        /\b(kya|kaise|kahan|kab|kaun|kyun|kyunki)\b/i,
        /\b(hai|hain|tha|thi|the|hoga|hogi)\b/i,
        /\b(mein|mera|meri|mere|humara|humari|humare)\b/i,
        /\b(yeh|woh|iska|iski|iske|uska|uski|uske)\b/i,
        /\b(kar|karna|karein|karenge|kijiye|dijiye|bataiye)\b/i,
        /\b(nahi|nahin|naa|mat|bilkul)\b/i,
        /\b(ji|haan|achha|theek|sahi|zaroor|zaruri)\b/i,
        /\b(ke liye|ke baare|ke saath|se pehle|ke baad)\b/i,
        /\b(samajh|baat|kaam|dost|ghar|rasta)\b/i,
        /\b(aur|lekin|ya|phir|toh|bhi|sirf)\b/i,
        /\b(bahut|thoda|zyada|kam|puri|poori)\b/i,
        /\b(pehle|abhi|baad|jaldi|kal)\b/i,
        /\b(namaste|dhanyavaad|shukriya|alvida)\b/i,
        /\b(policy\s+number\s+bata|claim\s+kar|insurance\s+ke)\b/i,
        /\b(durghatna|bima|suraksha|ilaj)\b/i,
    ];

    let hindiWordCount = 0;
    for (const pattern of hindiPatterns) {
        if (pattern.test(text)) {
            hindiWordCount++;
        }
        // If we find 2+ Hindi patterns, it's definitely Hindi/mixed
        if (hindiWordCount >= 2) return 'hi';
    }

    return 'en';
}

// ── Unicode-Aware Text Normalizer ──
// Preserves Hindi (Devanagari U+0900-097F) + Latin alphanumerics for echo matching.
// The old /[^a-z0-9 ]/g regex stripped ALL Hindi characters, breaking echo
// detection and causing infinite TTS feedback loops with Hindi content.
function normalizeForMatch(text) {
    if (!text) return '';
    return text
        .toLowerCase()
        .replace(/[^a-z0-9\u0900-\u097F ]/g, '')  // Keep Latin + Devanagari + spaces
        .replace(/\s+/g, ' ')                       // Collapse whitespace
        .trim();
}

// ── Deepgram TTS Helper (English only) ──
// Calls Deepgram REST TTS API and returns an audio blob URL
async function synthesizeDeepgramSpeech(text, apiKey) {
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

// ── Azure TTS Helper (Hindi + English) ──
// Calls our backend proxy which talks to Azure Speech Service
async function synthesizeAzureSpeech(text, language) {
    const baseUrl = import.meta.env.DEV
        ? `http://${window.location.hostname}:8000`
        : '';
    const res = await fetch(`${baseUrl}/api/azure-tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(`Azure TTS failed: ${res.status} ${err.error || res.statusText}`);
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
}

// ── Text Extraction Helper ──
// The LLM often outputs both English instructions (e.g., "Since the policy is not available, say:")
// AND the actual script (e.g., "कोई बात नहीं..."). We only want the TTS to speak the script.
function extractSpeakableText(text) {
    if (!text) return '';

    // 1. Look for text in quotes (the most common format for the actual script)
    const quoteMatches = text.match(/"([^"]+)"/g);
    if (quoteMatches && quoteMatches.length > 0) {
        // Return the last quoted string (usually the actual script)
        const lastQuote = quoteMatches[quoteMatches.length - 1];
        return lastQuote.replace(/"/g, '').trim();
    }

    // 2. Look for Devanagari text (Hindi script)
    // The instructions are almost always in English, while the script is in Hindi.
    // If we find a block of text with Devanagari characters, that's the script.
    const devanagariBlock = text.split('\n').find(line => /[\u0900-\u097F]/.test(line));
    if (devanagariBlock) {
        return devanagariBlock.replace(/^[A-Za-z\s:-]+/, '').trim(); // Remove leading English labels
    }

    // 3. Fallback: Speak the whole thing
    return text;
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

    // ── Fetch and cache Deepgram key (for English TTS fallback) ──
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

    // ── TTS Helper ──
    // Routes to Azure so the agent voice is consistently SwaraNeural (bilingual)
    const speakText = useCallback(async (text) => {
        if (!text || !text.trim()) return;

        // Strip markdown-style formatting for cleaner speech
        const cleanText = text
            .replace(/[─═*#_><]/g, '')
            .replace(/\n{2,}/g, '. ')
            .replace(/\n/g, ' ')
            .trim();

        if (!cleanText) return;

        // Extract ONLY the actual agent script, not the LLM's English instructions
        const speakableText = extractSpeakableText(cleanText);
        if (!speakableText) return;

        try {
            // Add Agent's speech to the UI transcript immediately since we drop echoes
            const offset = callTimerRef.current ? callElapsed : 0;
            const h = Math.floor(offset / 3600);
            const m = Math.floor((offset % 3600) / 60);
            const s = Math.floor(offset % 60);
            const timestamp = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

            wsProps.addTranscript({
                text: speakableText, // Display the extracted text in the UI transcript
                is_finalized: true,
                speaker: 'Agent',
                timestamp,
                offset,
            });

            // Ensure the backend also receives this transcript so the LLM remembers what it said
            const lang = detectLanguage(speakableText);
            if (wsProps.sendMessage) {
                // Send the extracted text, not the full instruction
                wsProps.sendMessage(speakableText, true, '0', offset, lang === 'hi' ? ['hi'] : ['en']);
            }

            // Route all speech through Azure for consistent bilingual voice
            console.log('🗣️ TTS: Routing to Azure Speech Service');
            let audioUrl;
            try {
                // Determine language hint for Azure (though SwaraNeural is bilingual)
                // Sending the extracted text specifically
                audioUrl = await synthesizeAzureSpeech(speakableText, lang === 'hi' ? 'hi' : 'en');
            } catch (azureErr) {
                console.warn('🗣️ TTS: Azure failed, falling back to Deepgram:', azureErr.message);
                const key = await ensureDgKey();
                audioUrl = await synthesizeDeepgramSpeech(speakableText, key);
            }

            // If AI was disabled while we were fetching, bail
            if (!aiEnabledRef.current) {
                if (audioUrl) URL.revokeObjectURL(audioUrl);
                return;
            }

            const audio = new Audio(audioUrl);
            audioRef.current = audio;
            setAiSpeaking(true);
            isSpeakingRef.current = true;
            
            recentlySpokenRef.current.push(normalizeForMatch(speakableText));
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
    }, [callElapsed, wsProps, ensureDgKey]);

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
            const normalized = normalizeForMatch(clean);
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
            // ── AI Echo Detection ──
            // When TTS plays through speakers, the microphone picks it up.
            // We must DROP these echo'd transcripts entirely so they don't loop.
            const timeSinceAiSpoke = Date.now() - lastAiSpeechEndTimeRef.current;
            
            // Check 1: AI is currently speaking or just finished (<800ms ago)
            // (Reduced from 5000ms to 800ms to avoid blocking fast human replies)
            if (isSpeakingRef.current || timeSinceAiSpoke < 800) {
                console.log(`🔇 Dropping echo (speaker ${event.speaker}, AI active):`, event.text?.slice(0, 40));
                return; // DROP
            }

            // Check 2: Text matches something we recently spoke
            if (event.text?.trim()) {
                const normText = normalizeForMatch(event.text);
                for (const spoken of recentlySpokenRef.current) {
                    if (normText && spoken && (spoken.includes(normText) || normText.includes(spoken) || spoken.length > 10 && normText.length > 10 && (spoken.startsWith(normText.substring(0, 10)) || normText.startsWith(spoken.substring(0, 10))))) {
                        console.log('🔇 Dropping echo (text match):', event.text?.slice(0, 40));
                        return; // DROP
                    }
                }
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
