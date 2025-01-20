import { createStore } from 'vuex';
import messages from './modules/messages';
import characters from './modules/characters';
import voiceRecordings from './modules/voiceRecordings';
import examples from './modules/examples';
import files from './modules/files';
import followUpResponses from './modules/followUpResponses';
import sessions from './modules/sessions';

export default createStore({
    modules: {
        messages,
        characters,
        voiceRecordings,
        examples,
        files,
        followUpResponses,
        sessions
    }
});