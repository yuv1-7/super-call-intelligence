/**
 * AudioWorklet processor that converts incoming audio to 16-bit PCM at 16kHz.
 * 
 * Receives audio from the AudioWorklet thread, downsamples from the browser's
 * native sample rate (typically 44100 or 48000) to 16kHz, converts to Int16,
 * and posts the resulting ArrayBuffer to the main thread.
 */
class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._buffer = [];
        // sampleRate is a global available in AudioWorkletGlobalScope
        this._inputSampleRate = sampleRate;
        this._targetSampleRate = 16000;
    }

    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) return true;

        // Take the first channel (mono)
        const channelData = input[0];
        if (!channelData || channelData.length === 0) return true;

        // Downsample to 16kHz
        const ratio = this._inputSampleRate / this._targetSampleRate;
        const targetLength = Math.floor(channelData.length / ratio);
        const pcm16 = new Int16Array(targetLength);

        for (let i = 0; i < targetLength; i++) {
            const srcIndex = Math.floor(i * ratio);
            // Clamp to [-1, 1] and convert to Int16 range
            const sample = Math.max(-1, Math.min(1, channelData[srcIndex]));
            pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }

        // Post the raw PCM buffer to the main thread
        this.port.postMessage(pcm16.buffer, [pcm16.buffer]);

        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor);
