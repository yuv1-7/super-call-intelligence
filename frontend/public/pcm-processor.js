/**
 * AudioWorklet processor that converts incoming stereo audio to 
 * interleaved 16-bit PCM at 16kHz for Deepgram multichannel transcription.
 * 
 * Expects 2-channel input (channel 0 = mic/Agent, channel 1 = system/Customer).
 * Downsamples from the browser's native sample rate to 16kHz and outputs
 * interleaved Int16 PCM (L, R, L, R, ...).
 */
class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        // sampleRate is a global available in AudioWorkletGlobalScope
        this._inputSampleRate = sampleRate;
        this._targetSampleRate = 16000;
    }

    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) return true;

        const ch0 = input[0]; // mic (Agent)
        const ch1 = input[1] || input[0]; // system audio (Customer), fallback to ch0 if mono

        if (!ch0 || ch0.length === 0) return true;

        // Downsample to 16kHz
        const ratio = this._inputSampleRate / this._targetSampleRate;
        const targetLength = Math.floor(ch0.length / ratio);

        // Interleaved stereo: [L0, R0, L1, R1, ...]
        const pcm16 = new Int16Array(targetLength * 2);

        for (let i = 0; i < targetLength; i++) {
            const srcIndex = Math.floor(i * ratio);

            const sampleL = Math.max(-1, Math.min(1, ch0[srcIndex]));
            const sampleR = Math.max(-1, Math.min(1, ch1[srcIndex]));

            pcm16[i * 2] = sampleL < 0 ? sampleL * 0x8000 : sampleL * 0x7FFF;
            pcm16[i * 2 + 1] = sampleR < 0 ? sampleR * 0x8000 : sampleR * 0x7FFF;
        }

        // Post the raw interleaved PCM buffer to the main thread
        this.port.postMessage(pcm16.buffer, [pcm16.buffer]);

        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor);
