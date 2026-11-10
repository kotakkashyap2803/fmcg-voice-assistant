
import { useCallback, useEffect, useRef, useState } from "react";

interface SpeechRecognitionResult {
    transcript: string;
    isListening: boolean;
    isSupported: boolean;
    error: string | null;
    startListening: () => void;
    stopListening: () => void;
    resetTranscript: () => void;
}

interface SpeechRecognitionInstance extends EventTarget {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    onresult: ((event: any) => void) | null;
    onerror: ((event: any) => void) | null;
    onend: (() => void) | null;
    start: () => void;
    stop: () => void;
    abort: () => void;
}

interface SpeechRecognitionConstructor {
    new (): SpeechRecognitionInstance;
}

declare global {
    interface Window {
        SpeechRecognition?: SpeechRecognitionConstructor;
        webkitSpeechRecognition?: SpeechRecognitionConstructor;
    }
}

export function useSpeechRecognition(
    language = "en-IN"
): SpeechRecognitionResult {
    const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

    const [transcript, setTranscript] = useState("");
    const [isListening, setIsListening] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const SpeechRecognitionAPI =
        typeof window !== "undefined"
            ? window.SpeechRecognition || window.webkitSpeechRecognition
            : undefined;

    const isSupported = Boolean(SpeechRecognitionAPI);

    useEffect(() => {
        if (!SpeechRecognitionAPI) return;

        const recognition = new SpeechRecognitionAPI();

        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = language;

        recognition.onresult = (event: any) => {
            let finalTranscript = "";

            for (
                let i = event.resultIndex;
                i < event.results.length;
                i++
            ) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                }
            }

            if (finalTranscript) {
                setTranscript((previous) =>
                    `${previous} ${finalTranscript}`.trim()
                );
            }
        };

        recognition.onerror = (event: any) => {
            setError(event.error || "Speech recognition failed.");
            setIsListening(false);
        };

        recognition.onend = () => {
            setIsListening(false);
        };

        recognitionRef.current = recognition;

        return () => {
            recognition.abort();
            recognitionRef.current = null;
        };
    }, [language, SpeechRecognitionAPI]);

    const startListening = useCallback(() => {
        if (!recognitionRef.current) {
            setError("Speech recognition is not supported in this browser.");
            return;
        }

        try {
            setError(null);
            setTranscript("");
            recognitionRef.current.start();
            setIsListening(true);
        } catch {
            setError("Unable to start microphone. Please try again.");
            setIsListening(false);
        }
    }, []);

    const stopListening = useCallback(() => {
        recognitionRef.current?.stop();
        setIsListening(false);
    }, []);

    const resetTranscript = useCallback(() => {
        setTranscript("");
        setError(null);
    }, []);

    return {
        transcript,
        isListening,
        isSupported,
        error,
        startListening,
        stopListening,
        resetTranscript,
    };
}
