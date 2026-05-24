import { useCallback, useEffect, useRef, useState } from "react";
import { submitCameraFrame } from "../api/settings";
import { FocusMode } from "../types";

export type BrowserCameraStatus =
  | "idle"
  | "requesting"
  | "streaming"
  | "denied"
  | "error";

const FRAME_UPLOAD_INTERVAL_MS = 5000;
const JPEG_QUALITY = 0.72;

type UseBrowserCameraOptions = {
  mode: FocusMode;
};

export const useBrowserCamera = ({ mode }: UseBrowserCameraOptions) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameTimerRef = useRef<number | null>(null);
  const wasStreamingRef = useRef(false);
  const [status, setStatus] = useState<BrowserCameraStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [framesSent, setFramesSent] = useState(0);

  const clearUploadTimer = useCallback(() => {
    if (frameTimerRef.current !== null) {
      window.clearInterval(frameTimerRef.current);
      frameTimerRef.current = null;
    }
  }, []);

  const stopStream = useCallback(() => {
    clearUploadTimer();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    wasStreamingRef.current = false;
  }, [clearUploadTimer]);

  const captureAndSendFrame = useCallback(async () => {
    if (mode === "break") {
      return;
    }

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
  }, [mode]);

  const startUploadTimer = useCallback(() => {
    clearUploadTimer();
    void captureAndSendFrame();
    frameTimerRef.current = window.setInterval(() => {
      void captureAndSendFrame();
    }, FRAME_UPLOAD_INTERVAL_MS);
  }, [captureAndSendFrame, clearUploadTimer]);

  const handleEnableCamera = useCallback(async () => {
    setErrorMessage("");
    setStatus("requesting");

    const constraintSets: Array<MediaStreamConstraints> = [
      {
        video: {
          facingMode: "user",
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      },
      {
        video: { facingMode: "user" },
        audio: false,
      },
    ];

    let lastError: unknown = null;

    for (let index = 0; index < constraintSets.length; index += 1) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia(constraintSets[index]);

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }

        setStatus("streaming");
        wasStreamingRef.current = true;
        if (mode !== "break") {
          startUploadTimer();
        }
        return;
      } catch (error) {
        lastError = error;
      }
    }

    stopStream();
    if (lastError instanceof DOMException && lastError.name === "NotAllowedError") {
      setStatus("denied");
      setErrorMessage("Camera permission was denied in the browser.");
      return;
    }
    setStatus("error");
    setErrorMessage(
      lastError instanceof Error ? lastError.message : "Failed to open camera",
    );
  }, [mode, startUploadTimer, stopStream]);

  useEffect(() => {
    if (status !== "streaming") {
      return;
    }

    if (mode === "break") {
      clearUploadTimer();
      return;
    }

    if (wasStreamingRef.current && frameTimerRef.current === null) {
      startUploadTimer();
    }
  }, [mode, status, clearUploadTimer, startUploadTimer]);

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
    sendFrameNow: captureAndSendFrame,
  };
};
