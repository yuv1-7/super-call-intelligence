import { useState, useRef, useCallback } from 'react';
import * as SpeechSDK from 'microsoft-cognitiveservices-speech-sdk';

/**
 * Custom hook for Azure Speech SDK with real-time transcription
 * and speaker diarization (ConversationTranscriber).
 *
 * Uses a short-lived token fetched from the backend (/api/speech-token)
 * so the API key never touches the browser.
 */
export function useAzureSpeech({ onTranscript }) {
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState(null);
    const transcriberRef = useRef(null);

    const fetchToken = async () => {
        const baseUrl = import.meta.env.DEV
            ? `http://${window.location.hostname}:8000`
            : '';
        const res = await fetch(`${baseUrl}/api/speech-token`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        return data; // { token, region }
    };

    const startListening = useCallback(async () => {
        try {
            setError(null);
            const { token, region } = await fetchToken();

            const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);

            // Set up auto-language detection for Hindi and Indian English. 
            // Note: pa-IN crashes ConversationTranscriber diarization, so it is handled phonetically.
            const autoDetectSourceLanguageConfig = SpeechSDK.AutoDetectSourceLanguageConfig.fromLanguages([
                "en-IN",
                "hi-IN"
            ]);

            // Enable continuous language identification
            speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_LanguageIdMode, "Continuous");

            // Tuning timeouts: restored to 700ms to ensure diarization has enough silence context
            speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "700");
            speechConfig.setProperty(SpeechSDK.PropertyId.Speech_SegmentationSilenceTimeoutMs, "700");

            // Prioritize latency over accuracy processing to reduce the "lag" feeling
            speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceResponse_PostProcessingOption, "TrueText");
            speechConfig.outputFormat = SpeechSDK.OutputFormat.Simple;
            let displayStream;
            let micStream;
            let audioContext;
            let transcriber;

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
                    throw new Error("Firefox doesn't support sharing system audio from the 'Entire Screen' option natively. Please use Chrome/Edge for this demo, or use a Virtual Audio Cable in Firefox.");
                }

                // Capture user's microphone
                micStream = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                    video: false
                });

                // Mix the two audio streams using Web Audio API
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const displaySource = audioContext.createMediaStreamSource(displayStream);
                const micSource = audioContext.createMediaStreamSource(micStream);
                const destination = audioContext.createMediaStreamDestination();

                displaySource.connect(destination);
                micSource.connect(destination);

                // Use the mixed stream for transcription
                const mixedStream = destination.stream;

                const audioConfig = SpeechSDK.AudioConfig.fromStreamInput(mixedStream);

                // Use FromConfig constructor to combine Diarization with Language Detection
                transcriber = SpeechSDK.ConversationTranscriber.FromConfig(speechConfig, autoDetectSourceLanguageConfig, audioConfig);

            } catch (err) {
                if (displayStream) displayStream.getTracks().forEach((track) => track.stop());
                if (micStream) micStream.getTracks().forEach((track) => track.stop());
                if (audioContext && audioContext.state !== 'closed') audioContext.close();

                if (err.name === 'NotAllowedError') {
                    throw new Error("Screen sharing or microphone was denied. " + err.message);
                }
                throw err;
            }

            // Store everything in the ref so we can clean up later
            transcriberRef.current = {
                transcriber,
                displayStream,
                micStream,
                audioContext
            };

            // ─── Interim results (partial) ─── //
            transcriber.transcribing = (s, e) => {
                if (e.result.reason === SpeechSDK.ResultReason.RecognizingSpeech) {
                    onTranscript?.({
                        text: e.result.text,
                        speaker: e.result.speakerId || 'Unknown',
                        isFinal: false,
                        offset: e.result.offset,
                        duration: e.result.duration,
                    });
                }
            };

            // ─── Final results ─── //
            transcriber.transcribed = (s, e) => {
                if (e.result.reason === SpeechSDK.ResultReason.RecognizedSpeech && e.result.text) {
                    onTranscript?.({
                        text: e.result.text,
                        speaker: e.result.speakerId || 'Unknown',
                        isFinal: true,
                        offset: e.result.offset,
                        duration: e.result.duration,
                    });
                }
            };

            transcriber.canceled = (s, e) => {
                if (e.reason === SpeechSDK.CancellationReason.Error) {
                    console.error('Azure Speech error:', e.errorDetails);
                    setError(e.errorDetails);
                }
                setIsListening(false);
            };

            transcriber.sessionStopped = () => {
                setIsListening(false);
            };

            await new Promise((resolve, reject) => {
                transcriber.startTranscribingAsync(
                    () => {
                        setIsListening(true);
                        console.log('🎙️ Azure Speech: transcription started with system audio share');
                        resolve();
                    },
                    (err) => {
                        console.error('Failed to start Azure Speech:', err);
                        setError(String(err));
                        reject(err);
                    }
                );
            });

            // Remove the redundant transcriberRef assignment
        } catch (err) {
            console.error('Azure Speech init error:', err);
            setError(err.message || String(err));
        }
    }, [onTranscript]);

    const stopListening = useCallback(() => {
        if (transcriberRef.current) {
            const { transcriber, displayStream, micStream, audioContext } = transcriberRef.current;

            if (transcriber) {
                transcriber.stopTranscribingAsync(
                    () => {
                        console.log('🎙️ Azure Speech: transcription stopped');
                        transcriber.close();
                    },
                    (err) => console.error('Error stopping transcription:', err)
                );
            }

            // Clean up custom streams and audio context
            if (displayStream) displayStream.getTracks().forEach(track => track.stop());
            if (micStream) micStream.getTracks().forEach(track => track.stop());
            if (audioContext && audioContext.state !== 'closed') audioContext.close();

            transcriberRef.current = null;
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
