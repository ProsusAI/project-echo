import store from "@/store";

class WebSocketService {
    constructor() {
        this.socket = null;
        this.sessionId = null;
    }

    async sendMessage(message) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.warn("WebSocket is not open. Cannot send message.");
        }
    }

    disconnect() {
        this.socket?.close();
    }

    async verifyConnection(sessionId) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN && this.sessionId === sessionId) return;
        await this.connect(sessionId);
    }

    async connect(sessionId) {
        if (!process.env.VUE_APP_API_URL) {
            throw new Error("WebSocket connection endpoint is not defined");
        }
        return new Promise((resolve, reject) => {
            if (this.socket && sessionId && this.sessionId === sessionId) {
                resolve();
                return;
            }

            let wsUrl =
                `${process.env.VUE_APP_API_URL}/api/v1/chat/ws`
                    .replace(/^http/, "ws")
                    .replace(/^https/, "wss");

            if (sessionId) {
                wsUrl += `?session_id=${sessionId}`;
            }

            try {
                this.socket = new WebSocket(wsUrl);

                this.socket.onmessage = this.onMessage.bind(this);
                this.socket.onerror = (error) => {
                    console.error("WebSocket Error:", error);
                    reject(new Error('WebSocket connection failed'));
                };
                this.socket.onclose = (event) => {
                    console.log("WebSocket connection closed:", event.code, event.reason);
                    store.dispatch("messages/setLoading", false);
                    reject(new Error(event.reason || 'WebSocket connection closed'));
                };
                this.socket.onopen = () => {
                    this.sessionId = sessionId;
                    resolve("WebSocket connection opened");
                };
            } catch (error) {
                console.error("WebSocket initialization error:", error);
                reject(error);
                store.dispatch("messages/setLoading", false);
            }
        });
    }

    onMessage(event) {
        const data = JSON.parse(event.data);
        const messageType = data.message_type;
        switch (messageType) {
            case "new_message":
                store.dispatch("messages/addMessage", {
                    id: Date.now(),
                    username: "Echo",
                    icon: "solar:soundwave-bold-duotone",
                    date: new Date().toLocaleString(),
                    content: data.content,
                    isUser: false,
                    files: null,
                    toolUsages: []
                });
                store.dispatch("messages/setLoading", true);
                break;
            case "update_message":
                store.dispatch("messages/updateLastMessage", data.content);
                break;
            case "loading_indicator":
                store.dispatch("messages/setLoading", data.status === "start");
                break;
            case "new_character":
                store.dispatch("characters/addCharacter", data.content);
                break;
            case "new_title":
                store.dispatch("voiceRecordings/setTitle", data.content.title);
                store.dispatch("voiceRecordings/setSubtitle", data.content.subtitle);
                break;
            case "new_voice_recording":
                store.dispatch("voiceRecordings/addVoiceRecording", data.content);
                break;
            case "delete_voice_recording":
                store.dispatch("voiceRecordings/deleteVoiceRecording", data.content.segment_index);
                break;
            case "new_session_connected":
                store.dispatch("messages/setCurrentSessionId", data.session_id);
                break;
            case "follow_up_responses":
                store.dispatch("followUpResponses/setFollowUpResponses", data.content);
                break;
            case "tool_progress":
            case "tool_error":
                store.dispatch("messages/upsertToolUsage", data);
                break;
            default:
                console.log("Unknown message type:", data);
        }
    }
}

export default new WebSocketService();
