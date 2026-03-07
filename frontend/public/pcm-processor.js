/**
 * AudioWorklet processor that converts incoming stereo audio to
 * interleaved 16-bit PCM at 16kHz for Deepgram multichannel transcription.
 *
 * Channel 0 (left)  = mic/Agent
 * Channel 1 (right) = system audio/Customer (Teams call)
 *
 * CROSS-CHANNEL DUCKING:
 * When the Customer channel (ch1) is active above a noise threshold,
 * the Agent channel (ch0) is silenced. This prevents the caller's voice
 * — playing through the laptop speakers — from bleeding back into the
 * mic and appearing as Agent speech.
 *
 * Parameters tunable via AudioWorkletNode port messages:
 *   { type: 'setThreshold', value: 0.015 }  — RMS level above which ch1 is "active"
 *   { type: 'setHoldMs',    value: 300 }     — ms to keep ch0 muted after ch1 goes quiet
 */
class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._inputSampleRate = sampleRate;
        this._targetSampleRate = 16000;

        // ── Ducking state ──────────────────────────────────────────
        // RMS threshold: ch1 signals above this level trigger ducking.
        // 0.015 ≈ -36 dBFS — sensitive enough for speech, ignores silence.
        this._threshold = 0.015;

        // Hold counter: keeps ch0 muted for this many samples after ch1 goes
        // quiet, preventing choppy edges when a sentence trails off.
        this._holdSamples = Math.round(0.3 * sampleRate); // 300 ms
        this._holdCountdown = 0;

        // Allow runtime tuning from the main thread
        this.port.onmessage = (e) => {
            if (e.data.type === 'setThreshold') this._threshold = e.data.value;
            if (e.data.type === 'setHoldMs')
                this._holdSamples = Math.round((e.data.value / 1000) * sampleRate);
        };
    }

    /**
     * Calculate the RMS (root mean square) energy of a Float32 audio frame.
     * Returns a value in [0, 1] — 0 = silence, 1 = full scale.
     */
    _rms(samples) {
        let sum = 0;
        for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
        return Math.sqrt(sum / samples.length);
    }

    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) return true;

        const ch0 = input[0];                  // mic   — Agent
        const ch1 = input[1] || input[0];      // system — Customer

        if (!ch0 || ch0.length === 0) return true;

        // ── Ducking decision ────────────────────────────────────────
        const customerLevel = this._rms(ch1);
        const customerActive = customerLevel > this._threshold;

        if (customerActive) {
            // Customer is speaking → reset hold timer
            this._holdCountdown = this._holdSamples;
        } else if (this._holdCountdown > 0) {
            // Customer just went quiet but still within hold window
            this._holdCountdown -= ch0.length;
        }

        const duck = customerActive || this._holdCountdown > 0;

        // ── Downsample + interleave → 16 kHz PCM ────────────────────
        const ratio = this._inputSampleRate / this._targetSampleRate;
        const targetLength = Math.floor(ch0.length / ratio);
        const pcm16 = new Int16Array(targetLength * 2);

        for (let i = 0; i < targetLength; i++) {
            const src = Math.floor(i * ratio);

            // Silence ch0 (agent mic) while customer is talking
            const rawL = duck ? 0 : Math.max(-1, Math.min(1, ch0[src]));
            const rawR = Math.max(-1, Math.min(1, ch1[src]));

            pcm16[i * 2] = rawL < 0 ? rawL * 0x8000 : rawL * 0x7FFF;
            pcm16[i * 2 + 1] = rawR < 0 ? rawR * 0x8000 : rawR * 0x7FFF;
        }

        this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
        return true;
    }
}

registerProcessor('pcm-processor', PCMProcessor);