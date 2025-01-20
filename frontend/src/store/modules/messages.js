const state = () => ({
    messages: [],
    loading: false,
    inputMessage: '',
    currentSessionId: null,
    lastMessageWasToolUsage: false
});

const mutations = {
    ADD_MESSAGE(state, message) {
        if (!message.toolUsages) {
            message.toolUsages = [];
        }
        state.messages.push(message);
        state.lastMessageWasToolUsage = false;
    },
    SET_MESSAGES(state, messages) {
        state.messages = messages;
    },
    UPDATE_LAST_MESSAGE(state, content) {
        const lastMessage = state.messages[state.messages.length - 1];
        if (lastMessage) {
            lastMessage.content += content;
        }
        state.lastMessageWasToolUsage = false;
    },
    UPSERT_TOOL_USAGE(state, toolUsage) {
        const { tool_call_id, message_type, content, icon } = toolUsage;
        const lastMessage = state.messages[state.messages.length - 1];
        state.lastMessageWasToolUsage = true;

        if (lastMessage && !lastMessage.isUser) {
            if (!lastMessage.toolUsages) {
                lastMessage.toolUsages = [];
            }
            const existingUsage = lastMessage.toolUsages.find(usage => usage.tool_call_id === tool_call_id);
            if (existingUsage) {
                Object.assign(existingUsage, { message_type, content, icon });
            } else {
                lastMessage.toolUsages.push({ tool_call_id, message_type, content, icon });
            }
        } else {
            state.messages.push({
                id: Date.now(),
                username: 'Echo',
                icon: 'solar:soundwave-bold-duotone',
                date: new Date().toLocaleString(),
                content: '',
                isUser: false,
                files: null,
                toolUsages: [{ tool_call_id, message_type, content, icon }]
            });
        }
    },
    SET_LOADING(state, status) {
        state.loading = status;
    },
    SET_INPUT_MESSAGE(state, message) {
        state.inputMessage = message;
    },
    SET_CURRENT_SESSION_ID(state, sessionId) {
        state.currentSessionId = sessionId;
    }
};

const actions = {
    addMessage({commit, state}, message) {
        if ((state.messages.length > 0 && state.messages[state.messages.length - 1].isUser) || state.messages.length === 0 || message.isUser || ( state.lastMessageWasToolUsage && state.messages[state.messages.length - 1].content.length > 0)) {
            commit('ADD_MESSAGE', message);
        } else {
            commit('UPDATE_LAST_MESSAGE', message.content);
        }
    },
    setMessages({commit}, messages) {
        commit('SET_MESSAGES', messages);
    },
    updateLastMessage({commit}, content) {
        commit('UPDATE_LAST_MESSAGE', content);
    },
    upsertToolUsage({commit}, toolUsage) {
        commit('UPSERT_TOOL_USAGE', toolUsage);
    },
    setLoading({commit}, status) {
        commit('SET_LOADING', status);
    },
    setInputMessage({commit}, message) {
        commit('SET_INPUT_MESSAGE', message);
    },
    setCurrentSessionId({commit}, sessionId) {
        commit('SET_CURRENT_SESSION_ID', sessionId);
    }
};

const getters = {
    allMessages: (state) => state.messages,
    messageCount: (state) => state.messages.length,
    isLoading: (state) => state.loading,
    currentSessionId: (state) => state.currentSessionId
};

export default {
    namespaced: true,
    state,
    mutations,
    actions,
    getters
};