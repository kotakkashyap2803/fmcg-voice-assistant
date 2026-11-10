
import { useCallback, useEffect, useRef, useState } from "react";

interface SpeechSynthesisResult {
    isSpeaking: boolean;
    isSupported: boolean;
    speak: (text: string, language?: string) => void;
    stopSpeaking: () => void;
}

export function useSpeechSynthesis(): SpeechSynthesisResult {
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isSupported, setIsSupported] = useState(false);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

    useEffect(() => {
        setIsSupported(
            typeof window !== "undefined" &&
            "speechSynthesis" in window
        );

        return () => {
            window.speechSynthesis?.cancel();
        };
    }, []);

    const speak = useCallback(
        (text: string, language = "en-IN") => {
            if (!("speechSynthesis" in window) || !text.trim()) {
                return;
            }

            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = language;
            utterance.rate = 0.95;
            utterance.pitch = 1;
            utterance.volume = 1;

            utterance.onstart = () => setIsSpeaking(true);
            utterance.onend = () => setIsSpeaking(false);
            utterance.onerror = () => setIsSpeaking(false);

            utteranceRef.current = utterance;
            window.speechSynthesis.speak(utterance);
        },
        []
    );

    const stopSpeaking = useCallback(() => {
        window.speechSynthesis?.cancel();
        utteranceRef.current = null;
        setIsSpeaking(false);
    }, []);

    return {
        isSpeaking,
        isSupported,
        speak,
        stopSpeaking,
    };
}
