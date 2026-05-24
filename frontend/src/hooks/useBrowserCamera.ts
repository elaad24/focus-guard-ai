import { useCallback, useEffect, useRef, useState } from "react";
import { submitCameraFrame } from "../api/settings";

export type BrowserCameraStatus =
  | "idle"
  | "requesting"
  | "streaming"
  | "denied"
  | "error";

const FRAME_UPLOAD_INTERVAL_MS = 5000;
const JPEG_QUALITY = 0.72;

export const useBrowserCamera = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameTimerRef = useRef<number | null>(null);
  const [status, setStatus] = useState<BrowserCameraStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [framesSent, setFramesSent] = useState(0);

  const stopStream = useCallback(() => {
    if (frameTimerRef.current !== null) {
      window.clearInterval(frameTimerRef.current);
      frameTimerRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const captureAndSendFrame = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return;
    }

    const width = video.videoWidth;
    const height = video.videoHeight;
    if (width === 0 || height === 0) {
      return;
    }

    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    context.drawImage(video, 0, 0, width, height);

    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob((result) => resolve(result), "image/jpeg", JPEG_QUALITY);
    });
    if (!blob) {
      return;
    }

    try {
      await submitCameraFrame(blob);
      setFramesSent((count) => count + 1);
    } catch {
      // Keep streaming locally even if one upload fails.
    }
  }, []);

  const handleEnableCamera = useCallback(async () => {
    setErrorMessage("");
    setStatus("requesting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setStatus("streaming");
      void captureAndSendFrame();
      frameTimerRef.current = window.setInterval(() => {
        void captureAndSendFrame();
      }, FRAME_UPLOAD_INTERVAL_MS);
    } catch (error) {
      stopStream();
      if (error instanceof DOMException && error.name === "NotAllowedError") {
        setStatus("denied");
        setErrorMessage("Camera permission was denied in the browser.");
        return;
      }
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "Failed to open camera");
    }
  }, [captureAndSendFrame, stopStream]);

  useEffect(() => {
    return () => {
      stopStream();
    };
  }, [stopStream]);

  return {
    videoRef,
    canvasRef,
    status,
    errorMessage,
    framesSent,
    handleEnableCamera,
    stopStream,
  };
};
