const state = () => ({
    followUpResponses: [],
});

const mutations = {
    SET_FOLLOW_UP_RESPONSES(state, responses) {
        state.followUpResponses = responses;
    }
};

const actions = {
    setFollowUpResponses({ commit }, responses) {
        commit('SET_FOLLOW_UP_RESPONSES', responses);
    },
    clearFollowUpResponses({ commit }) {
        commit('SET_FOLLOW_UP_RESPONSES', []);
    }
};

const getters = {
    allFollowUpResponses: (state) => state.followUpResponses
};

export default {
    namespaced: true,
    state,
    mutations,
    actions,
    getters
};