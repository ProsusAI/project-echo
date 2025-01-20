const state = {
    sessions: [],
    loading: false,
    error: null,
    currentPage: 1,
    itemsPerPage: 10,
    hasMore: true,
    currentSession: null
};

const getters = {
    getSessions: state => state.sessions,
    isLoading: state => state.loading,
    getError: state => state.error,
    hasMoreSessions: state => state.hasMore,
    getCurrentSession: state => state.currentSession
};

const actions = {
    async fetchSessions({ commit, state }, { page = 1, reset = false } = {}) {
        try {
            commit('setLoading', true);
            commit('setError', null);
            
            const skip = (page - 1) * state.itemsPerPage;
            const response = await fetch(
                `${process.env.VUE_APP_API_URL}/api/v1/session/sessions/?skip=${skip}&limit=${state.itemsPerPage}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Failed to fetch sessions');
            }

            const sessions = await response.json();
            
            commit('setSessions', { sessions, reset });
            commit('setCurrentPage', page);
            commit('setHasMore', sessions.length === state.itemsPerPage);
            
        } catch (error) {
            commit('setError', error.message);
            console.error('Error fetching sessions:', error);
        } finally {
            commit('setLoading', false);
        }
    },

    async deleteSession({ commit }, sessionId) {
        try {
            commit('setLoading', true);
            commit('setError', null);

            const response = await fetch(
                `${process.env.VUE_APP_API_URL}/api/v1/session/sessions/${sessionId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Failed to delete session');
            }

            return true;
        } catch (error) {
            commit('setError', error.message);
            console.error('Error deleting session:', error);
            throw error;
        } finally {
            commit('setLoading', false);
        }
    },

    async loadMoreSessions({ dispatch, state }) {
        if (state.hasMore && !state.loading) {
            await dispatch('fetchSessions', { page: state.currentPage + 1 });
        }
    },

    async loadConversation({ commit }, sessionId) {
        try {
            commit('setLoading', true);
            commit('setError', null);

            const response = await fetch(
                `${process.env.VUE_APP_API_URL}/api/v1/session/sessions/${sessionId}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Failed to load session');
            }

            const session = await response.json();
            commit('setCurrentSession', session);
            return session;
        } catch (error) {
            commit('setError', error.message);
            console.error('Error loading session:', error);
            return null;
        } finally {
            commit('setLoading', false);
        }
    },

    resetSessions({ commit }) {
        commit('setSessions', { sessions: [], reset: true });
        commit('setCurrentPage', 1);
        commit('setHasMore', true);
        commit('setCurrentSession', null);
    }
};

const mutations = {
    setSessions(state, { sessions, reset }) {
        if (reset) {
            state.sessions = sessions;
        } else {
            state.sessions = [...state.sessions, ...sessions];
        }
    },
    setLoading(state, loading) {
        state.loading = loading;
    },
    setError(state, error) {
        state.error = error;
    },
    setCurrentPage(state, page) {
        state.currentPage = page;
    },
    setHasMore(state, hasMore) {
        state.hasMore = hasMore;
    },
    setCurrentSession(state, session) {
        state.currentSession = session;
    }
};

export default {
    namespaced: true,
    state,
    getters,
    actions,
    mutations
}; 