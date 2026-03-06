import { useState, useRef, useCallback } from 'react';

/**
 * Custom hook for Sarvam AI Saaras V3 real-time transcription.
 *
 * Captures mic + system audio, mixes them, converts to PCM s16le 16kHz,
 * and streams raw audio to the backend WebSocket proxy (/sarvam-stream).
 * The backend forwards audio to Sarvam's API and relays transcripts back.
 */
export function useAzureSpeech({ onTranscript }) {
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState(null);
    const sessionRef = useRef(null);

    const startListening = useCallback(async () => {
        try {
            setError(null);
            let displayStream;
            let micStream;
            let audioContext;
            let sarvamWs;

            try {
                // Capture system audio via screen share
                displayStream = await navigator.mediaDevices.getDisplayMedia({
                    video: true,
                    audio: {
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: false
                    }
                });

                if (displayStream.getAudioTracks().length === 0) {
                    displayStream.getTracks().forEach((track) => track.stop());
                    throw new Error("No system audio detected. Please share a tab or window with audio, or use Chrome/Edge.");
                }

                // Capture user's microphone
                micStream = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                    video: false
                });

                // Mix the two audio streams using Web Audio API at 16kHz for Sarvam
                audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
                const displaySource = audioContext.createMediaStreamSource(displayStream);
                const micSource = audioContext.createMediaStreamSource(micStream);

                // Use ScriptProcessorNode to capture raw PCM audio
                // Buffer size of 4096 at 16kHz = ~256ms chunks
                const processor = audioContext.createScriptProcessor(4096, 1, 1);
                const merger = audioContext.createChannelMerger(2);

                displaySource.connect(merger, 0, 0);
                micSource.connect(merger, 0, 0);
                merger.connect(processor);
                processor.connect(audioContext.destination);

                // Connect to backend Sarvam proxy WebSocket
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsHost = import.meta.env.DEV
                    ? `${window.location.hostname}:8000`
                    : window.location.host;
                sarvamWs = new WebSocket(`${wsProtocol}//${wsHost}/sarvam-stream`);

                // Fallback offset counter (backend provides utterance_id)
                let utteranceOffset = 0;

                // Handle incoming transcripts from Sarvam via backend
                sarvamWs.onmessage = (event) => {
                    try {
                        const msg = JSON.parse(event.data);
                        console.log('🔍 Sarvam WS raw message:', JSON.stringify(msg).slice(0, 300));

                        // Backend sends: {type: 'transcript', text, is_final, speaker_id, language_code, utterance_id}
                        // Key: ALL Sarvam data messages are FINAL (no partials).
                        // utterance_id is a monotonic counter from the backend for unique de-duplication.
                        if (msg.type === 'transcript' && msg.text) {
                            const transcriptEvent = {
                                text: msg.text,
                                speaker: msg.speaker_id || 'Speaker',
                                isFinal: true,  // Sarvam only sends finals
                                offset: (msg.utterance_id || utteranceOffset++) * 10000,
                                duration: 0,
                            };
                            console.log('📝 Sending to onTranscript:', transcriptEvent);
                            onTranscript?.(transcriptEvent);
                        } else if (msg.type === 'vad') {
                            // VAD signals from Sarvam (start_speech / end_speech)
                            console.log(`🔊 VAD: ${msg.signal}`);
                        } else if (msg.type === 'error') {
                            console.error('Sarvam STT error:', msg.text || msg.data);
                            setError(msg.text || 'Sarvam STT error');
                        }
                    } catch (e) {
                        console.error('Failed to parse Sarvam message:', e);
                    }
                };

                sarvamWs.onerror = (err) => {
                    console.error('Sarvam WebSocket error:', err);
                    setError('Connection to Sarvam STT failed');
                };

                sarvamWs.onclose = () => {
                    console.log('🎙️ Sarvam STT: WebSocket closed');
                };

                // Wait for WebSocket to open before sending audio
                await new Promise((resolve, reject) => {
                    sarvamWs.onopen = () => {
                        console.log('🎙️ Sarvam STT: connected to backend proxy');
                        resolve();
                    };
                    const origOnError = sarvamWs.onerror;
                    sarvamWs.onerror = (err) => {
                        origOnError?.(err);
                        reject(new Error('Failed to connect to Sarvam STT backend'));
                    };
                    setTimeout(() => reject(new Error('Sarvam STT connection timeout')), 10000);
                });

                // Stream raw PCM audio to the backend
                processor.onaudioprocess = (e) => {
                    if (sarvamWs.readyState !== WebSocket.OPEN) return;

                    const float32Data = e.inputBuffer.getChannelData(0);

                    // Convert float32 [-1, 1] to int16 [-32768, 32767] (PCM s16le)
                    const int16Data = new Int16Array(float32Data.length);
                    for (let i = 0; i < float32Data.length; i++) {
                        const s = Math.max(-1, Math.min(1, float32Data[i]));
                        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }

                    sarvamWs.send(int16Data.buffer);
                };

            } catch (err) {
                if (displayStream) displayStream.getTracks().forEach((track) => track.stop());
                if (micStream) micStream.getTracks().forEach((track) => track.stop());
                if (audioContext && audioContext.state !== 'closed') audioContext.close();
                if (sarvamWs && sarvamWs.readyState === WebSocket.OPEN) sarvamWs.close();

                if (err.name === 'NotAllowedError') {
                    throw new Error("Screen sharing or microphone was denied. " + err.message);
                }
                throw err;
            }

            // Store everything in the ref so we can clean up later
            sessionRef.current = {
                sarvamWs,
                displayStream,
                micStream,
                audioContext,
            };

            setIsListening(true);
            console.log('🎙️ Sarvam STT: transcription started');

        } catch (err) {
            console.error('Sarvam STT init error:', err);
            setError(err.message || String(err));
        }
    }, [onTranscript]);

    const stopListening = useCallback(() => {
        if (sessionRef.current) {
            const { sarvamWs, displayStream, micStream, audioContext } = sessionRef.current;

            if (sarvamWs && sarvamWs.readyState === WebSocket.OPEN) {
                sarvamWs.close();
                console.log('🎙️ Sarvam STT: transcription stopped');
            }

            if (displayStream) displayStream.getTracks().forEach(track => track.stop());
            if (micStream) micStream.getTracks().forEach(track => track.stop());
            if (audioContext && audioContext.state !== 'closed') audioContext.close();

            sessionRef.current = null;
        }
        setIsListening(false);
    }, []);

    const toggleListening = useCallback(() => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    }, [isListening, startListening, stopListening]);

    return {
        isListening,
        error,
        startListening,
        stopListening,
        toggleListening,
    };
}
