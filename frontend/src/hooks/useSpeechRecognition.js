import { useState, useRef, useCallback } from 'react';

/**
 * Custom hook for Deepgram real-time transcription with channel-based diarization.
 * 
 * Uses TWO separate audio channels for deterministic speaker identification:
 *   - Channel 0 (left)  = Microphone → Agent
 *   - Channel 1 (right) = System audio → Customer
 * 
 * Connects directly to Deepgram's WebSocket API with multichannel=true.
 * Deepgram transcribes each channel independently, so speaker labels
 * are always correct regardless of voice similarity.
 * 
 * Supports Hindi + English + Hinglish (code-switching) via language=multi
 * with the Nova-3 model.
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

            // 1. Fetch token from backend
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

                // 3. Keep streams as SEPARATE channels using ChannelMergerNode
                //    Channel 0 (left)  = mic → Agent
                //    Channel 1 (right) = system audio → Customer
                audioContext = new AudioContext();
                const micSource = audioContext.createMediaStreamSource(micStream);
                const displaySource = audioContext.createMediaStreamSource(displayStream);

                // Merge into a 2-channel (stereo) stream
                const merger = audioContext.createChannelMerger(2);
                micSource.connect(merger, 0, 0);      // mic → channel 0 (Agent)
                displaySource.connect(merger, 0, 1);   // system → channel 1 (Customer)

                // 4. Load AudioWorklet for stereo PCM extraction
                await audioContext.audioWorklet.addModule('/pcm-processor.js');
                const workletNode = new AudioWorkletNode(audioContext, 'pcm-processor', {
                    // Ensure the worklet receives 2 channels
                    channelCount: 2,
                    channelCountMode: 'explicit',
                    channelInterpretation: 'discrete',
                });

                merger.connect(workletNode);
                // Don't connect to destination — we don't want to play the audio back

                // 5. Open WebSocket directly to Deepgram with multichannel
                const dgParams = new URLSearchParams({
                    model: 'nova-3',
                    language: 'multi',
                    multichannel: 'true',
                    channels: '2',
                    smart_format: 'true',
                    interim_results: 'true',
                    endpointing: '700',
                    encoding: 'linear16',
                    sample_rate: '16000',
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
                    console.log('🎙️ Deepgram: WebSocket connected (multichannel: ch0=Agent, ch1=Customer)');
                    setIsListening(true);

                    // Route interleaved stereo PCM from AudioWorklet → Deepgram
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

                            // Multichannel: channel_index[0] tells us which channel
                            // Channel 0 = mic = Agent, Channel 1 = system = Customer
                            const channelIdx = msg.channel_index?.[0] ?? 0;
                            const speaker = String(channelIdx); // "0" = Agent, "1" = Customer

                            // Round offset for stable deduplication
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
