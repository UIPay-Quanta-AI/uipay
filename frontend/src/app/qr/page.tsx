'use client';

import jsQR from 'jsqr';
import { Image as ImageIcon, Loader2, QrCode } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import api, { getApiErrorMessage } from '@/services/api';
import { useAuthHydration, useAuthStore } from '@/store/auth';
import { useSendStore } from '@/store/send';

type ScanState = 'idle' | 'scanning' | 'resolving' | 'error';

export default function QrScanPage() {
  const router = useRouter();
  const hasHydrated = useAuthHydration();
  const accessToken = useAuthStore((state) => state.accessToken);
  const setSource = useSendStore((state) => state.setSource);

  const [state, setState] = useState<ScanState>('idle');
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // guards against a stray requestAnimationFrame tick calling validate()
  // again after a code was already found and the effect started tearing
  // camera access down
  const handledRef = useRef(false);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace('/signin');
    }
  }, [hasHydrated, accessToken, router]);

  const stopCamera = () => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  useEffect(() => stopCamera, []);

  const handleDecoded = async (code: string) => {
    if (handledRef.current) return;
    handledRef.current = true;
    stopCamera();

    setState('resolving');
    setError(null);
    try {
      const res = await api.post('/qr/validate', { qrCode: code });
      const { businessName, category, type, amount } = res.data.data;
      setSource({
        method: 'qr',
        qrCode: code,
        name: businessName,
        detail: category,
        fixedAmount: type === 'dynamic' ? amount : undefined,
      });
      router.push('/send/amount');
    } catch (err) {
      handledRef.current = false;
      setState('error');
      setError(getApiErrorMessage(err));
    }
  };

  const scanFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState !== video.HAVE_ENOUGH_DATA) {
      rafRef.current = requestAnimationFrame(scanFrame);
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = jsQR(imageData.data, imageData.width, imageData.height);

    if (code?.data) {
      handleDecoded(code.data);
      return;
    }

    rafRef.current = requestAnimationFrame(scanFrame);
  };

  const handleStartScan = async () => {
    setError(null);
    handledRef.current = false;

    // Camera access is blocked outright on an insecure origin (plain http,
    // anything other than localhost) - mobile browsers won't even prompt
    // for permission, they just don't expose getUserMedia at all. This is
    // the case when testing over a LAN IP (http://192.168.x.x:3000); it
    // works fine once the site is served over https (production, or a
    // tunnel like ngrok during dev).
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setState('error');
      setError(
        'Camera access needs a secure (https) connection - it\'s blocked on a plain http address like this one. Use Upload From Gallery instead, or test camera scanning on the deployed https site.',
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setState('scanning');
      rafRef.current = requestAnimationFrame(scanFrame);
    } catch (err) {
      setState('error');
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        setError(
          'Camera permission was denied. Allow camera access for this site in your browser settings, or use Upload From Gallery instead.',
        );
      } else if (err instanceof DOMException && err.name === 'NotFoundError') {
        setError('No camera was found on this device. Use Upload From Gallery instead.');
      } else {
        setError(
          'Could not access the camera. Check your browser/site camera permission, or use Upload From Gallery instead.',
        );
      }
    }
  };

  // Phone camera photos can be 12+ megapixels. Running getImageData/jsQR at
  // full resolution allocates a huge buffer and can block the main thread
  // for a long time on a mid-range phone - it looks like the app froze, it's
  // just a very slow synchronous decode. A QR code is easily readable at a
  // much smaller size, so cap the longest side before decoding.
  const MAX_DECODE_DIMENSION = 1200;

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    handledRef.current = false;
    setError(null);
    setState('resolving');

    const objectUrl = URL.createObjectURL(file);
    const image = new window.Image();

    image.onload = () => {
      URL.revokeObjectURL(objectUrl);

      const scale = Math.min(
        1,
        MAX_DECODE_DIMENSION / Math.max(image.width, image.height),
      );
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(image.width * scale);
      canvas.height = Math.round(image.height * scale);
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        setState('error');
        setError('Could not read that image. Try another one.');
        return;
      }

      // Let the "Checking code..." spinner actually paint before the
      // (still synchronous) decode work runs.
      requestAnimationFrame(() => {
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height);

        if (code?.data) {
          handleDecoded(code.data);
        } else {
          setState('error');
          setError('No QR code found in that image. Try another one.');
        }
      });
    };

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      setState('error');
      setError(
        'Could not open that image (unsupported format). Try a screenshot or a PNG/JPEG photo instead.',
      );
    };

    image.src = objectUrl;
  };

  if (!hasHydrated || !accessToken) return null;

  return (
    <main className="relative flex h-screen w-screen flex-col items-center overflow-hidden bg-[var(--color-dark)] px-6 py-10">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-[var(--color-primary)] opacity-30 blur-3xl" />

      <div className="relative z-10 flex h-full w-full flex-col items-center">
        <div className="mt-16 flex h-72 w-72 items-center justify-center overflow-hidden rounded-3xl border-2 border-[var(--color-primary)]/40 bg-black/40">
          {state === 'scanning' ? (
            <video
              ref={videoRef}
              muted
              playsInline
              className="h-full w-full object-cover"
            />
          ) : state === 'resolving' ? (
            <Loader2 className="h-16 w-16 animate-spin text-[var(--color-primary)]" />
          ) : (
            <QrCode className="h-32 w-32 text-[var(--color-primary)]" strokeWidth={1.2} />
          )}
        </div>

        <p className="animate-rise-in mt-8 text-center text-lg text-[var(--color-light)]">
          {state === 'scanning'
            ? 'Aim Your Camera At QR Code'
            : state === 'resolving'
              ? 'Checking code...'
              : 'Aim Your Camera At QR Code'}
        </p>

        {error && (
          <p className="animate-shake mt-4 max-w-xs text-center text-sm text-red-400">
            {error}
          </p>
        )}

        <canvas ref={canvasRef} className="hidden" />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleUpload}
          className="hidden"
        />

        <div className="mt-auto flex w-full flex-col gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 rounded-full bg-[rgba(var(--color-primary-rgb),0.15)] py-4 font-semibold text-[var(--color-primary)] transition-transform active:scale-95"
          >
            <ImageIcon className="h-5 w-5" />
            Upload From Gallery
          </button>
          <button
            type="button"
            onClick={handleStartScan}
            disabled={state === 'scanning' || state === 'resolving'}
            className="rounded-full bg-[var(--color-primary)] py-4 font-semibold uppercase text-[var(--color-dark)] transition-transform active:scale-95 disabled:opacity-60"
          >
            Scan QR Code
          </button>
          <button
            type="button"
            onClick={() => {
              stopCamera();
              router.push('/dashboard');
            }}
            className="text-center text-white/50 underline"
          >
            Cancel
          </button>
        </div>
      </div>
    </main>
  );
}
