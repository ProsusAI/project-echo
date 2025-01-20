const state = () => ({
    voiceRecordings: [],
    title: 'Voice Recordings',
    subtitle: null,
    currentSegmentIndex: 0,
    isPlaying: false,
    audio: null,
});

const mutations = {
    ADD_VOICE_RECORDING(state, recording) {
        const existingIndex = state.voiceRecordings.findIndex(rec => rec.segment_index === recording.segment_index);
        if (existingIndex !== -1) {
            // Update existing recording
            state.voiceRecordings.splice(existingIndex, 1, recording);
        } else {
            // Add new recording
            state.voiceRecordings.push(recording);
        }
        this.commit('voiceRecordings/REINDEX_ALL_SEGMENTS');
    },
    SET_VOICE_RECORDINGS(state, recordings) {
        state.voiceRecordings = recordings;
        this.commit('voiceRecordings/REINDEX_ALL_SEGMENTS');
    },
    SET_TITLE(state, title) {
        state.title = title;
    },
    SET_SUBTITLE(state, subtitle) {
        state.subtitle = subtitle;
    },
    SET_CURRENT_SEGMENT_INDEX(state, index) {
        state.currentSegmentIndex = index;
    },
    SET_IS_PLAYING(state, isPlaying) {
        state.isPlaying = isPlaying;
    },
    SET_AUDIO_ELEMENT(state, audio) {
        state.audio = audio;
    },
    REINDEX_ALL_SEGMENTS(state) {
        // Sort all segments first by scene_index, then by position_in_scene
        state.voiceRecordings.sort((a, b) => {
            if (a.scene_index !== b.scene_index) {
                return a.scene_index - b.scene_index;
            }
            return (a.position_in_scene || 0) - (b.position_in_scene || 0);
        });

        // Reindex segments
        let globalIndex = 0;
        let currentSceneIndex = null;
        state.voiceRecordings.forEach(segment => {
            if (currentSceneIndex !== segment.scene_index) {
                currentSceneIndex = segment.scene_index;
            }
            segment.segment_index = globalIndex;
            globalIndex++;
        });
    },
    DELETE_VOICE_RECORDING(state, segmentIndex) {
        state.voiceRecordings = state.voiceRecordings.filter(rec => rec.segment_index !== segmentIndex);
        this.commit('voiceRecordings/SET_CURRENT_SEGMENT_INDEX', 0);
    },
};

const actions = {
    addVoiceRecording({commit}, recording) {
        commit('ADD_VOICE_RECORDING', recording);
    },
    setVoiceRecordings({commit}, recordings) {
        commit('SET_VOICE_RECORDINGS', recordings);
    },
    setTitle({commit}, title) {
        commit('SET_TITLE', title);
    },
    setSubtitle({commit}, subtitle) {
        commit('SET_SUBTITLE', subtitle);
    },
    setCurrentSegmentIndex({commit}, index) {
        commit('SET_CURRENT_SEGMENT_INDEX', index);
    },
    setIsPlaying({commit}, isPlaying) {
        commit('SET_IS_PLAYING', isPlaying);
    },
    initializeAudio({commit, state, dispatch}) {
        if (!state.audio) {
            const audio = new Audio();
            audio.addEventListener('ended', () => {
                dispatch('handleAudioEnded');
            });
            commit('SET_AUDIO_ELEMENT', audio);
        }
    },
    playAudio({state, dispatch}) {
        const {audio} = state;
        if (audio) {
            audio.play();
            dispatch('setIsPlaying', true);
        }
    },
    pauseAudio({state, dispatch}) {
        const {audio} = state;
        if (audio) {
            audio.pause();
            dispatch('setIsPlaying', false);
        }
    },
    loadAudio({state, dispatch}, audio_segment_url) {
        const {audio} = state;
        if (audio) {
            audio.src = audio_segment_url;
            audio.load();
            audio.oncanplay = () => {
                dispatch('playAudio');
            };
        }
    },
    handleAudioEnded({ state, dispatch }) {
        if (state.currentSegmentIndex < state.voiceRecordings.length - 1) {
            dispatch('playNextSegment');
        } else {
            dispatch('setIsPlaying', false);
        }
    },
    playNextSegment({state, dispatch}) {
        if (state.currentSegmentIndex < state.voiceRecordings.length - 1) {
            dispatch('setCurrentSegmentIndex', state.currentSegmentIndex + 1);
        } else {
            dispatch('setIsPlaying', false);
        }
    },
    playPreviousSegment({state, dispatch}) {
        if (state.currentSegmentIndex > 0) {
            dispatch('setCurrentSegmentIndex', state.currentSegmentIndex - 1);
        }
    },
    deleteVoiceRecording({commit}, segmentIndex) {
        commit('DELETE_VOICE_RECORDING', segmentIndex);
    }
};

const getters = {
    allVoiceRecordings: (state) => state.voiceRecordings,
    voiceRecordingCount: (state) => state.voiceRecordings.length,
    title: (state) => state.title,
    subtitle: (state) => state.subtitle,
    currentSegmentIndex: (state) => state.currentSegmentIndex,
    isPlaying: (state) => state.isPlaying,
    currentRecording: (state) => state.voiceRecordings[state.currentSegmentIndex] || {}
};

export default {
    namespaced: true,
    state,
    mutations,
    actions,
    getters
};
