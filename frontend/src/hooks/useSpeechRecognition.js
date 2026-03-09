import { useState, useRef, useCallback } from 'react';

/**
 * Custom hook for Deepgram real-time transcription with channel-based diarization.
 * 
 * Uses TWO separate audio channels for deterministic speaker identification:
 *   - Channel 0 (left)  = Microphone → Agent
 *   - Channel 1 (right) = System audio → Customer
 * 
 * KEY FIX: echoCancellation: true on the mic stream prevents the caller's audio
 * (playing through laptop speakers) from bleeding back into the agent's mic channel.
 */
export function useDeepgramSpeech({ onTranscript }) {
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState(null);
    const sessionRef = useRef(null);

    const fetchToken = async () => {
        const baseUrl = import.meta.env.DEV
            ? `http://${window.location.hostname}:8000`
            : '';
        const res = await fetch(`${baseUrl}/api/deepgram-token`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        return data.token;
    };

    const startListening = useCallback(async () => {
        try {
            setError(null);

            const token = await fetchToken();

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

                // FIX: echoCancellation removes the caller's voice that's playing through
                // your laptop speakers from leaking back into your microphone (Agent channel).
                micStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                    },
                    video: false
                });

                audioContext = new AudioContext();
                const micSource = audioContext.createMediaStreamSource(micStream);
                const displaySource = audioContext.createMediaStreamSource(displayStream);

                const merger = audioContext.createChannelMerger(2);
                micSource.connect(merger, 0, 0);      // mic → channel 0 (Agent)
                displaySource.connect(merger, 0, 1);   // system → channel 1 (Customer)

                await audioContext.audioWorklet.addModule('/pcm-processor.js');
                const workletNode = new AudioWorkletNode(audioContext, 'pcm-processor', {
                    channelCount: 2,
                    channelCountMode: 'explicit',
                    channelInterpretation: 'discrete',
                });

                merger.connect(workletNode);

                const dgParams = new URLSearchParams({
                    model: 'nova-3',
                    language: 'multi',
                    multichannel: 'true',
                    endpointing: '1500',              // Lowered to 1500ms for near real-time latency
                    encoding: 'linear16',
                    sample_rate: '16000',
                });

                const dgUrl = `wss://api.deepgram.com/v1/listen?${dgParams.toString()}`;
                const dgSocket = new WebSocket(dgUrl, ['token', token]);

                sessionRef.current = {
                    dgSocket,
                    displayStream,
                    micStream,
                    audioContext,
                    workletNode,
                };

                dgSocket.onopen = () => {
                    console.log('🎙️ Deepgram: WebSocket connected (multichannel: ch0=Agent, ch1=Customer)');
                    setIsListening(true);

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
                            const isFinal = msg.is_final === true;
                            const start = msg.start || 0;

                            const channelIdx = msg.channel_index?.[0] ?? 0;
                            const speaker = String(channelIdx);

                            const stableOffset = Math.round(start * 100) / 100;

                            console.log(
                                `${isFinal ? '📝 FINAL' : '💬 Partial'} ` +
                                `[Ch${channelIdx} → ${channelIdx === 0 ? 'Agent' : 'Customer'}]: ` +
                                `${text.slice(0, 60)}`
                            );

                            onTranscript?.({
                                text,
                                speaker,
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

                displayStream.getVideoTracks()[0]?.addEventListener('ended', () => {
                    stopListening();
                });

            } catch (err) {
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

            if (workletNode) {
                workletNode.port.onmessage = null;
                workletNode.disconnect();
            }

            if (dgSocket && dgSocket.readyState === WebSocket.OPEN) {
                dgSocket.send(new Uint8Array(0));
                dgSocket.close();
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