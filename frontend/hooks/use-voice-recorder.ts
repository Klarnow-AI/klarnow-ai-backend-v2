"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const SpeechRecognitionAPI =
  typeof window !== "undefined"
    ? (window as Window & { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ??
      (
        window as Window & {
          webkitSpeechRecognition?: typeof SpeechRecognition;
        }
      ).webkitSpeechRecognition
    : undefined;

export type UseVoiceRecorderOptions = {
  onTranscription: (text: string) => void;
  onError?: (message: string) => void;
};

export function useVoiceRecorder({
  onTranscription,
  onError,
}: UseVoiceRecorderOptions) {
  const [isRecording, setIsRecording] = useState(false);
  const [supported, setSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const accumulatedRef = useRef<string>("");
  const interimRef = useRef<string>("");
  const onTranscriptionRef = useRef(onTranscription);
  onTranscriptionRef.current = onTranscription;

  useEffect(() => {
    setSupported(!!SpeechRecognitionAPI);
  }, []);

  const finishWithTranscript = useCallback(() => {
    const final = accumulatedRef.current.trim();
    const interim = interimRef.current.trim();
    const fullText = [final, interim].filter(Boolean).join(" ");
    accumulatedRef.current = "";
    interimRef.current = "";
    if (fullText) {
      onTranscriptionRef.current(fullText);
    }
  }, []);

  const stopRecording = useCallback(() => {
    const rec = recognitionRef.current;
    if (!rec) return;
    setIsRecording(false);
    try {
      rec.stop();
    } catch {
      // Ignore
    }
    // onend will fire after stop() processes; it will call finishWithTranscript
  }, []);

  const startRecording = useCallback(() => {
    if (!SpeechRecognitionAPI) {
      onError?.("Voice input is not supported in this browser");
      return;
    }

    if (recognitionRef.current) {
      stopRecording();
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const transcript = result[0]?.transcript ?? "";
        if (result.isFinal) {
          accumulatedRef.current = accumulatedRef.current
            ? `${accumulatedRef.current} ${transcript}`
            : transcript;
          interimRef.current = "";
        } else {
          interimRef.current = transcript;
        }
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const msg =
        event.error === "not-allowed"
          ? "Microphone access is required for voice input"
          : event.error === "no-speech"
            ? "No speech detected"
            : `Voice input error: ${event.error}`;
      onError?.(msg);
      recognitionRef.current = null;
      accumulatedRef.current = "";
      interimRef.current = "";
      setIsRecording(false);
    };

    recognition.onend = () => {
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null;
        setIsRecording(false);
        finishWithTranscript();
      }
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      accumulatedRef.current = "";
      interimRef.current = "";
      setIsRecording(true);
    } catch (e) {
      onError?.(e instanceof Error ? e.message : "Failed to start voice input");
    }
  }, [onError, stopRecording, finishWithTranscript]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // Ignore
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording,
    supported,
    toggle: isRecording ? stopRecording : startRecording,
  };
}
