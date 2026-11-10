
import api from "./api";

export interface ConversationResponse {
    success: boolean;
    message: string;
    data: {
        id: number;
        retailer: number;
        retailer_name: string;
        channel: string;
        language: string;
        status: string;
        [key: string]: any;
    };
}

export interface AssistantMessageResponse {
    success: boolean;
    conversation_id?: number;
    response?: string;
    message?: string;
    [key: string]: any;
}

export interface ConversationCompletionResponse {
    success: boolean;
    message: string;
    data: {
        id: number;
        status: string;
        outcome: string;
        summary: string;
        ended_at: string;
    };
}

// Start a new conversation
export const startConversation = async (
    retailerId: number,
    language: string
): Promise<ConversationResponse> => {
    const response = await api.post<ConversationResponse>(
        "/conversations/start/",
        {
            retailer_id: retailerId,
            channel: "VOICE",
            language,
        }
    );

    return response.data;
};

// Send a message to the AI assistant
export const sendMessage = async (
    conversationId: number,
    message: string
): Promise<AssistantMessageResponse> => {
    const response = await api.post<AssistantMessageResponse>(
        "/assistant/message/",
        {
            conversation_id: conversationId,
            message,
        }
    );

    return response.data;
};

// Complete a conversation.
// The backend determines the outcome and generates the summary.
export const completeConversation = async (
    conversationId: number
): Promise<ConversationCompletionResponse> => {
    const response = await api.post<ConversationCompletionResponse>(
        `/conversations/${conversationId}/complete/`,
        {}
    );

    return response.data;
};
