const state = {
    imageFiles: [],
    otherFiles: []
};

const mutations = {
    ADD_IMAGE_FILE(state, file) {
        state.imageFiles.push(file);
    },
    ADD_OTHER_FILE(state, file) {
        state.otherFiles.push(file);
    },
    REMOVE_IMAGE_FILE(state, fileUrl) {
        state.imageFiles = state.imageFiles.filter(file => file.url !== fileUrl);
    },
    REMOVE_OTHER_FILE(state, fileUrl) {
        state.otherFiles = state.otherFiles.filter(file => file.url !== fileUrl);
    },
    CLEAR_FILES(state) {
        state.imageFiles = [];
        state.otherFiles = [];
    }
};

const actions = {
    async uploadFile({commit}, {file, sessionId}) {
        try {
            const fileType = file.type.split('/')[0];
            const uploadResponse = await fetch(`${process.env.VUE_APP_API_URL}/api/v1/session/upload/${file.name}?session_id=${sessionId}`,
                {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: file
                }
            );
            const s3Info = await uploadResponse.json();


            if (uploadResponse.ok) {
                const addFileResponse = await fetch(`${process.env.VUE_APP_API_URL}/api/v1/session/add_file_to_session/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        s3_key: s3Info.file_s3_key,
                        file_type: fileType
                    })
                });
                const {file_presigned_url} = await addFileResponse.json();

                if (fileType === 'image') {
                    commit('ADD_IMAGE_FILE', {name: file.name, type: file.type, url: file_presigned_url});
                } else {
                    commit('ADD_OTHER_FILE', {name: file.name, type: file.type, url: file_presigned_url});
                }
            } else {
                alert("File upload failed. Please try again.");
            }
        } catch (error) {
            console.error("File upload failed:", error);
            alert("File upload failed. Please try again.");
        }
    },
    async removeFile({commit}, {file, sessionId}) {
        try {
            const response = await fetch(`${process.env.VUE_APP_API_URL}/api/v1/session/remove_file_from_session/?session_id=${sessionId}&file_name=${file.name}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                if (file.type.startsWith('image')) {
                    commit('REMOVE_IMAGE_FILE', file.url);
                } else {
                    commit('REMOVE_OTHER_FILE', file.url);
                }
            } else {
                console.error("File removal failed:", await response.json());
                alert("File removal failed. Please try again.");
            }
        } catch (error) {
            console.error("File removal failed:", error);
            alert("File removal failed. Please try again.");
        }
    },
    clearFiles({commit}) {
        commit('CLEAR_FILES');
    }
};

export default {
    namespaced: true,
    state,
    mutations,
    actions
};
