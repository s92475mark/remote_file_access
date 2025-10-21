document.addEventListener('DOMContentLoaded', (event) => {
    (function() {
        const fileInput = document.getElementById('fileInput');
        const uploadButton = document.getElementById('uploadButton');
        const progressBar = document.getElementById('progressBar');
        const uploadStatus = document.getElementById('uploadStatus');

        let selectedFile = null;
        const API_URL = window.STREAMLIT_API_URL; // Use global variable injected by Streamlit
        const AUTH_TOKEN = window.STREAMLIT_AUTH_TOKEN; // Use global variable injected by Streamlit
        let CHUNK_SIZE = 1024 * 1024 * 5; // Default 5MB, can be updated by backend init response

        // --- Streamlit Communication (Basic) ---
        // Function to send messages back to the Streamlit parent frame
        function sendMessageToStreamlit(type, payload) {
            if (window.parent) {
                window.parent.postMessage({
                    streamlit: true,
                    type: type,
                    payload: payload
                }, '*');
            }
        }

        // --- Event Listeners ---
        fileInput.addEventListener('change', (event) => {
            selectedFile = event.target.files[0];
            if (selectedFile) {
                uploadButton.disabled = false;
                uploadStatus.textContent = `已選擇檔案: ${selectedFile.name} (${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)`;
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
                uploadStatus.classList.remove('error', 'success');
            } else {
                uploadButton.disabled = true;
                uploadStatus.textContent = '請選擇檔案';
            }
        });

        uploadButton.addEventListener('click', async () => {
            if (!selectedFile) {
                uploadStatus.textContent = '請先選擇檔案！';
                return;
            }
            if (!AUTH_TOKEN) {
                uploadStatus.textContent = '錯誤：未提供認證 token。';
                sendMessageToStreamlit('error', 'Authentication token missing.');
                return;
            }

            uploadButton.disabled = true;
            fileInput.disabled = true;
            uploadStatus.textContent = '正在初始化上傳...';
            uploadStatus.classList.remove('error', 'success');
            sendMessageToStreamlit('status', 'Initializing upload...');

            try {
                // 1. Init Upload
                const initResponse = await fetch(`${API_URL}/files/upload`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${AUTH_TOKEN}`
                    },
                    body: JSON.stringify({
                        filename: selectedFile.name,
                        file_size: selectedFile.size,
                        file_type: selectedFile.type
                    })
                });

                if (!initResponse.ok) {
                    const errorData = await initResponse.json();
                    throw new Error(`初始化失敗: ${errorData.message || initResponse.statusText}`);
                }
                const initData = await initResponse.json();
                const uploadId = initData.upload_id;
                CHUNK_SIZE = initData.chunk_size || CHUNK_SIZE; // Use backend suggested chunk size
                const uploadChunkUrl = initData.upload_url; // e.g., /api/files/upload/chunk/{upload_id}

                uploadStatus.textContent = `上傳 ID: ${uploadId}，開始上傳檔案塊...`;
                sendMessageToStreamlit('status', `Upload ID: ${uploadId}, starting chunk upload.`);

                // 2. Upload Chunks
                let uploadedBytes = 0;
                let start = 0;
                const totalChunks = Math.ceil(selectedFile.size / CHUNK_SIZE);
                let chunkNum = 0;

                while (start < selectedFile.size) {
                    const end = Math.min(start + CHUNK_SIZE, selectedFile.size);
                    const chunk = selectedFile.slice(start, end);

                    const chunkResponse = await fetch(`${API_URL}${uploadChunkUrl.replace('{upload_id}', uploadId)}`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${AUTH_TOKEN}`,
                            'Content-Range': `bytes ${start}-${end - 1}/${selectedFile.size}`,
                            'Content-Type': 'application/octet-stream' // Indicate raw binary data
                        },
                        body: chunk
                    });

                    if (!chunkResponse.ok) {
                        const errorData = await chunkResponse.json();
                        throw new Error(`檔案塊上傳失敗 (Chunk ${chunkNum + 1}/${totalChunks}): ${errorData.message || chunkResponse.statusText}`);
                    }

                    uploadedBytes += chunk.size;
                    const progress = (uploadedBytes / selectedFile.size) * 100;
                    progressBar.style.width = `${progress}%`;
                    progressBar.textContent = `${progress.toFixed(0)}%`;
                    uploadStatus.textContent = `正在上傳: ${progress.toFixed(0)}% (${chunkNum + 1}/${totalChunks} 塊)`;
                    sendMessageToStreamlit('progress', progress.toFixed(0));

                    start = end;
                    chunkNum++;
                }

                // 3. Complete Upload
                uploadStatus.textContent = '所有檔案塊已上傳，正在完成上傳...';
                sendMessageToStreamlit('status', 'All chunks uploaded, finalizing...');

                const completeResponse = await fetch(`${API_URL}/files/upload`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${AUTH_TOKEN}`
                    },
                    body: JSON.stringify({ upload_id: uploadId })
                });

                if (!completeResponse.ok) {
                    const errorData = await completeResponse.json();
                    throw new Error(`完成上傳失敗: ${errorData.message || completeResponse.statusText}`);
                }
                const completeData = await completeResponse.json();
                uploadStatus.textContent = `上傳成功！檔案 ID: ${completeData.id}`; // Assuming completeData has 'id'
                uploadStatus.classList.remove('error');
                uploadStatus.classList.add('success');
                sendMessageToStreamlit('success', completeData);

            } catch (error) {
                uploadStatus.textContent = `上傳失敗: ${error.message}`;
                uploadStatus.classList.remove('success');
                uploadStatus.classList.add('error');
                sendMessageToStreamlit('error', error.message);
            } finally {
                uploadButton.disabled = false;
                fileInput.disabled = false;
            }
        });

        // Notify Streamlit that the component is ready to receive data
        // This is important for Streamlit to know when to send the initial data
        sendMessageToStreamlit('ready', 'Component loaded.');

    })();
});
