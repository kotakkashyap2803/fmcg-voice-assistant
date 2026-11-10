
import { useCallback, useState } from "react";

import {
    startConversation as startConversationApi,
    sendMessage as sendMessageApi,
    completeConversation as completeConversationApi,
} from "../services/conversationService";

import { useSpeechRecognition } from "./useSpeechRecognition";
import { useSpeechSynthesis } from "./useSpeechSynthesis";

interface VoiceAgentMessage {
    role: "user" | "assistant";
    text: string;
}

interface ConversationCompletion {
    outcome: string;
    summary: string;
}

interface VoiceAgentResponse {
    conversationId: number | null;
    messages: VoiceAgentMessage[];
    completion: ConversationCompletion | null;
    isLoading: boolean;
    error: string | null;
    transcript: string;
    isListening: boolean;
    isSpeaking: boolean;
    isSupported: boolean;
    startSession: () => Promise<void>;
    sendUserMessage: (message: string) => Promise<void>;
    sendTranscript: () => Promise<void>;
    finishSession: () => Promise<void>;
    startListening: () => void;
    stopListening: () => void;
    stopSpeaking: () => void;
    resetTranscript: () => void;
}

const getSpeechLanguage = (language: string) => {
    return language === "hi" ? "hi-IN" : "en-IN";
};

export function useVoiceAgent(
    retailerId: number,
    language = "en"
): VoiceAgentResponse {

    const recognition = useSpeechRecognition(
        getSpeechLanguage(language)
    );

    const synthesis = useSpeechSynthesis();

    const [conversationId, setConversationId] = useState<number | null>(null);
    const [messages, setMessages] = useState<VoiceAgentMessage[]>([]);
    const [completion, setCompletion] =
        useState<ConversationCompletion | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Start conversation and request the AI greeting.
    const startSession = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            setMessages([]);
            setCompletion(null);

            const result = await startConversationApi(
                retailerId,
                language
            );

            const newConversationId = Number(result?.data?.id);

            if (
                !result?.success ||
                !Number.isFinite(newConversationId) ||
                newConversationId <= 0
            ) {
                throw new Error(
                    "The server did not return a valid conversation ID."
                );
            }

            setConversationId(newConversationId);

            const initialMessage =
                language === "hi" ? "αñ¿αñ«αñ╕αÑìαññαÑç" : "Hello";

            const greetingResult = await sendMessageApi(
                newConversationId,
                initialMessage
            );

            if (!greetingResult?.success || !greetingResult?.response) {
                throw new Error(
                    "The conversation started, but the AI greeting could not be generated."
                );
            }

            const greeting = greetingResult.response;

            setMessages([
                {
                    role: "assistant",
                    text: greeting,
                },
            ]);

            synthesis.speak(
                greeting,
                getSpeechLanguage(language)
            );

        } catch (err: any) {
            setError(
                err?.response?.data?.message ||
                err?.message ||
                "Unable to start the conversation."
            );
        } finally {
            setIsLoading(false);
        }
    }, [retailerId, language, synthesis.speak]);

    // Send a text or voice-transcribed message.
    const sendUserMessage = useCallback(
        async (message: string) => {
            const cleanMessage = message.trim();

            if (!cleanMessage || !conversationId || isLoading) {
                return;
            }

            try {
                setIsLoading(true);
                setError(null);

                setMessages((previous) => [
                    ...previous,
                    {
                        role: "user",
                        text: cleanMessage,
                    },
                ]);

                const result = await sendMessageApi(
                    conversationId,
                    cleanMessage
                );

                if (!result?.success || !result?.response) {
                    throw new Error(
                        "The assistant did not return a valid response."
                    );
                }

                const assistantResponse = result.response;

                setMessages((previous) => [
                    ...previous,
                    {
                        role: "assistant",
                        text: assistantResponse,
                    },
                ]);

                synthesis.speak(
                    assistantResponse,
                    getSpeechLanguage(language)
                );

            } catch (err: any) {
                setError(
                    err?.response?.data?.message ||
                    err?.message ||
                    "Unable to send your message."
                );
            } finally {
                setIsLoading(false);
            }
        },
        [conversationId, language, isLoading, synthesis.speak]
    );

    // Send the recorded speech transcript.
    const sendTranscript = useCallback(async () => {
        const message = recognition.transcript.trim();

        if (!message) {
            setError("Please speak something before sending.");
            return;
        }

        recognition.stopListening();

        await sendUserMessage(message);

        recognition.resetTranscript();
    }, [
        recognition.transcript,
        recognition.stopListening,
        recognition.resetTranscript,
        sendUserMessage,
    ]);

    // Complete the conversation and retain the backend-generated result.
    const finishSession = useCallback(async () => {
        if (!conversationId) return;

        try {
            setIsLoading(true);
            setError(null);

            recognition.stopListening();
            synthesis.stopSpeaking();

            const result = await completeConversationApi(conversationId);

            if (!result?.success || !result?.data) {
                throw new Error(
                    result?.message || "The conversation could not be completed."
                );
            }

            setCompletion({
                outcome: result.data.outcome,
                summary: result.data.summary,
            });

            setConversationId(null);

        } catch (err: any) {
            setError(
                err?.response?.data?.message ||
                err?.message ||
                "Unable to complete the conversation."
            );
        } finally {
            setIsLoading(false);
        }
    }, [
        conversationId,
        recognition.stopListening,
        synthesis.stopSpeaking,
    ]);

    return {
        conversationId,
        messages,
        completion,
        isLoading,
        error,

        transcript: recognition.transcript,
        isListening: recognition.isListening,
        isSpeaking: synthesis.isSpeaking,

        isSupported: recognition.isSupported,

        startSession,
        sendUserMessage,
        sendTranscript,
        finishSession,

        startListening: recognition.startListening,
        stopListening: recognition.stopListening,
        stopSpeaking: synthesis.stopSpeaking,
        resetTranscript: recognition.resetTranscript,
    };
}
