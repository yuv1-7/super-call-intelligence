import { useState, useRef, useCallback } from 'react';

/**
 * Custom hook for Deepgram real-time transcription with speaker diarization.
 * 
 * Connects directly to Deepgram's WebSocket API from the browser using a
 * short-lived JWT token fetched from the backend. Uses AudioWorklet for
 * off-main-thread PCM extraction (16-bit, 16kHz mono).
 * 
 * Supports Hindi + English + Hinglish (code-switching) via language=multi
 * with the Nova-3 model, and real-time speaker diarization.
 */
export function useDeepgramSpeech({ onTranscript }) {
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState(null);
    const sessionRef = useRef(null);
    // Track the last known speaker across utterances for interim results
    // that may not have diarization data yet
    const lastSpeakerRef = useRef(0);

    const fetchToken = async () => {
        const baseUrl = import.meta.env.DEV
            ? `http://${window.location.hostname}:8000`
            : '';
        const res = await fetch(`${baseUrl}/api/deepgram-token`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        return data.token;
    };

    /**
     * Determine the dominant speaker for a Deepgram utterance.
     * Each word in a finalized result has a `speaker` field (integer).
     * For interim results, words may lack speaker data — we fall back
     * to the last known speaker from a previous finalized result.
     */
    const getDominantSpeaker = (words, isFinal) => {
        if (!words || words.length === 0) return lastSpeakerRef.current;

        // Check if any word actually has speaker info
        const wordsWithSpeaker = words.filter(w => w.speaker !== undefined && w.speaker !== null);

        if (wordsWithSpeaker.length === 0) {
            // No diarization data (common in interim results) — use last known speaker
            return lastSpeakerRef.current;
        }

        // Count speaker occurrences
        const counts = {};
        for (const w of wordsWithSpeaker) {
            const s = w.speaker;
            counts[s] = (counts[s] || 0) + 1;
        }

        let dominant = lastSpeakerRef.current;
        let maxCount = 0;
        for (const [speaker, count] of Object.entries(counts)) {
            if (count > maxCount) {
                maxCount = count;
                dominant = Number(speaker);
            }
        }

        // Update last known speaker when we get finalized results
        if (isFinal) {
            lastSpeakerRef.current = dominant;
        }

        return dominant;
    };

    const startListening = useCallback(async () => {
        try {
            setError(null);
            lastSpeakerRef.current = 0; // Reset speaker tracking for new session

            // 1. Fetch short-lived token from backend
            const token = await fetchToken();

            // 2. Capture system audio (screen share) + microphone
            let displayStream;
            let micStream;
            let audioContext;

            try {
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
                    throw new Error(
                        "Your browser doesn't support sharing system audio from this source. " +
                        "Please use Chrome/Edge and select a tab or window with audio."
                    );
                }

                micStream = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                    video: false
                });

                // 3. Mix the two audio streams using Web Audio API
                // Use native sample rate — AudioWorklet handles downsampling to 16kHz
                audioContext = new AudioContext();
                const displaySource = audioContext.createMediaStreamSource(displayStream);
                const micSource = audioContext.createMediaStreamSource(micStream);

                // 4. Load AudioWorklet for off-main-thread PCM extraction
                await audioContext.audioWorklet.addModule('/pcm-processor.js');
                const workletNode = new AudioWorkletNode(audioContext, 'pcm-processor');

                // Connect both sources → worklet
                displaySource.connect(workletNode);
                micSource.connect(workletNode);
                // Don't connect to destination — we don't want to play the audio back

                // 5. Open WebSocket directly to Deepgram
                const dgParams = new URLSearchParams({
                    model: 'nova-3',
                    language: 'multi',
                    diarize: 'true',
                    smart_format: 'true',
                    interim_results: 'true',
                    endpointing: '700',
                    encoding: 'linear16',
                    sample_rate: '16000',
                    channels: '1',
                });

                const dgUrl = `wss://api.deepgram.com/v1/listen?${dgParams.toString()}`;

                const dgSocket = new WebSocket(dgUrl, ['token', token]);

                // Store session for cleanup
                sessionRef.current = {
                    dgSocket,
                    displayStream,
                    micStream,
                    audioContext,
                    workletNode,
                };

                // 6. Wire up events
                dgSocket.onopen = () => {
                    console.log('🎙️ Deepgram: WebSocket connected');
                    setIsListening(true);

                    // Route PCM data from AudioWorklet → Deepgram WebSocket
                    workletNode.port.onmessage = (event) => {
                        if (dgSocket.readyState === WebSocket.OPEN) {
                            dgSocket.send(event.data);
                        }
                    };
                };

                dgSocket.onmessage = (event) => {
                    try {
                        const msg = JSON.parse(event.data);

                        if (msg.type === 'Results') {
                            const alt = msg.channel?.alternatives?.[0];
                            if (!alt || !alt.transcript) return;

                            const text = alt.transcript;
                            const words = alt.words || [];
                            const isFinal = msg.is_final === true;
                            const start = msg.start || 0;

                            // Debug: log raw speaker data from Deepgram
                            if (isFinal && words.length > 0) {
                                const speakerIds = words.map(w => w.speaker);
                                const uniqueSpeakers = [...new Set(speakerIds)];
                                console.log(
                                    `🔍 Deepgram raw diarization — speakers: [${uniqueSpeakers.join(',')}], ` +
                                    `word count: ${words.length}, text: "${text.slice(0, 50)}"`
                                );
                            }

                            const speaker = getDominantSpeaker(words, isFinal);

                            // Round offset to 2 decimal places for stable deduplication
                            // between interim and final results
                            const stableOffset = Math.round(start * 100) / 100;

                            console.log(
                                `${isFinal ? '📝 FINAL' : '💬 Partial'} [Speaker ${speaker}]: ${text.slice(0, 60)}`
                            );

                            onTranscript?.({
                                text,
                                speaker: String(speaker),
                                isFinal,
                                offset: stableOffset,
                            });
                        }
                    } catch (err) {
                        console.error('Deepgram message parse error:', err);
                    }
                };

                dgSocket.onerror = (event) => {
                    console.error('Deepgram WebSocket error:', event);
                    setError('Deepgram connection error. Check your API key and network.');
                };

                dgSocket.onclose = (event) => {
                    console.log(`🎙️ Deepgram: WebSocket closed (code=${event.code}, reason=${event.reason})`);
                    if (event.code !== 1000 && event.code !== 1005) {
                        setError(`Deepgram disconnected unexpectedly (code: ${event.code})`);
                    }
                    setIsListening(false);
                };

                // Stop listening if user stops screen share
                displayStream.getVideoTracks()[0]?.addEventListener('ended', () => {
                    stopListening();
                });

            } catch (err) {
                // Cleanup on setup failure
                if (displayStream) displayStream.getTracks().forEach((track) => track.stop());
                if (micStream) micStream.getTracks().forEach((track) => track.stop());
                if (audioContext && audioContext.state !== 'closed') audioContext.close();

                if (err.name === 'NotAllowedError') {
                    throw new Error('Screen sharing or microphone was denied. ' + err.message);
                }
                throw err;
            }
        } catch (err) {
            console.error('Deepgram init error:', err);
            setError(err.message || String(err));
        }
    }, [onTranscript]);

    const stopListening = useCallback(() => {
        if (sessionRef.current) {
            const { dgSocket, displayStream, micStream, audioContext, workletNode } = sessionRef.current;

            // Disconnect worklet
            if (workletNode) {
                workletNode.port.onmessage = null;
                workletNode.disconnect();
            }

            // Send close signal to Deepgram (empty byte signals end-of-stream)
            if (dgSocket && dgSocket.readyState === WebSocket.OPEN) {
                dgSocket.send(new Uint8Array(0));
                dgSocket.close();
            }

            // Clean up media tracks and audio context
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
