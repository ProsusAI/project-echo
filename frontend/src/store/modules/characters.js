const state = () => ({
    characters: []
});

const mutations = {
    ADD_CHARACTER(state, character) {
        state.characters.push(character);
    },
    SET_CHARACTERS(state, characters) {
        state.characters = characters;
    }
};

const actions = {
    addCharacter({ commit }, character) {
        commit('ADD_CHARACTER', character);
    },
    setCharacters({ commit }, characters) {
        commit('SET_CHARACTERS', characters);
    }
};

const getters = {
    allCharacters: (state) => state.characters,
    characterCount: (state) => state.characters.length
};

export default {
    namespaced: true,
    state,
    mutations,
    actions,
    getters
};