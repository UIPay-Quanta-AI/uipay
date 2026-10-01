import { useCallback, useRef, useState } from 'react';

// Chrome/Edge support opus-in-webm; Safari only supports mp4/aac. Trying
// them in order and letting MediaRecorder fall back to its own default
// covers both without the caller needing to know which one landed.
const PREFERRED_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
  'audio/ogg;codecs=opus',
];

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined;
  return PREFERRED_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

export type RecorderStatus = 'idle' | 'requesting' | 'recording' | 'error';

export function useAudioRecorder() {
  const [status, setStatus] = useState<RecorderStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const start = useCallback(async () => {
    setErrorMessage(null);
    setStatus('requesting');

    // Mic access is blocked outright on an insecure origin (plain http,
    // anything other than localhost) - same restriction that blocks camera
    // access elsewhere in this app. It works fine over https (production,
    // or a tunnel like ngrok during dev).
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setErrorMessage(
        "Microphone access needs a secure (https) connection - it's blocked on a plain http address like this one.",
      );
      setStatus('error');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus('recording');
    } catch (err) {
      setErrorMessage(
        err instanceof DOMException && err.name === 'NotAllowedError'
          ? 'Microphone permission was denied. Allow microphone access for this site in your browser settings.'
          : 'Could not access the microphone. Check your browser permissions and try again.',
      );
      setStatus('error');
      stopStream();
    }
  }, [stopStream]);

  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        chunksRef.current = [];
        stopStream();
        setStatus('idle');
        resolve(blob.size > 0 ? blob : null);
      };

      recorder.stop();
    });
  }, [stopStream]);

  const cancel = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.onstop = null;
      recorder.stop();
    }
    chunksRef.current = [];
    stopStream();
    setStatus('idle');
  }, [stopStream]);

  return { status, errorMessage, start, stop, cancel };
}
