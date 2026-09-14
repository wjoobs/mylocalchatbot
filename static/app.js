// =========================
// 전역 상태
// =========================

let currentChatId = null;
let renamingChatId = null;


// =========================
// DOM 요소
// =========================

const messageInput =
    document.getElementById("message");

const chat =
    document.getElementById("chat");

const sendButton =
    document.getElementById("sendButton");

const fileButton =
    document.getElementById("fileButton");

const fileInput =
    document.getElementById("fileInput");

const filePreview =
    document.getElementById("filePreview");

let selectedFile = null;

const renameModal =
    document.getElementById("renameModal");

const renameInput =
    document.getElementById("renameInput");

const renameError =
    document.getElementById("renameError");

const renameCancelButton =
    document.getElementById("renameCancelButton");

const renameSaveButton =
    document.getElementById("renameSaveButton");


// =========================
// 공통
// =========================

function renderMarkdown(content) {

    if (window.marked) {

        return marked.parse(content);
    }

    return content
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}


function showWelcome() {

    chat.innerHTML = `
        <div class="welcome">

            <div class="welcome-icon">
                🤖
            </div>

            <h2>
                무엇을 도와드릴까요?
            </h2>

            <p>
                이 AI는 여러분의 PC에서
                실행되는 로컬 LLM입니다.
            </p>

        </div>
    `;
}


// =========================
// 메시지 추가
// =========================

function addMessage(role, content) {

    const welcome =
        document.querySelector(".welcome");

    if (welcome) {
        welcome.remove();
    }


    const message =
        document.createElement("div");

    message.className =
        `message ${role}-message`;


    const avatar =
        document.createElement("div");

    avatar.className =
        "avatar";

    avatar.textContent =
        role === "user"
            ? "👤"
            : "🤖";


    const contentWrapper =
        document.createElement("div");

    contentWrapper.className =
        "message-wrapper";


    const messageContent =
        document.createElement("div");

    messageContent.className =
        "message-content";


    if (role === "assistant") {

        messageContent.innerHTML =
            renderMarkdown(content);

    } else {

        messageContent.textContent =
            content;
    }


    contentWrapper.appendChild(
        messageContent
    );


    if (role === "assistant") {

        const copyButton =
            document.createElement("button");

        copyButton.className =
            "copy-button";

        copyButton.textContent =
            "📋";

        copyButton.title =
            "답변 복사";


        copyButton.onclick =
            async () => {

                await navigator.clipboard.writeText(
                    messageContent.innerText
                );


                copyButton.textContent =
                    "✓";


                setTimeout(() => {

                    copyButton.textContent =
                        "📋";

                }, 1500);
            };


        contentWrapper.appendChild(
            copyButton
        );
    }


    message.appendChild(avatar);
    message.appendChild(contentWrapper);

    chat.appendChild(message);


    scrollToBottom();


    return messageContent;
}


// =========================
// 메시지 전송
// =========================

async function sendMessage() {
    const message =
        messageInput.value.trim();

    if (!message && !selectedFile) {
        return;
    }

    if (currentChatId === null) {
        const response =
            await fetch("/chats", {
                method: "POST"
            });

        const newChatData =
            await response.json();

        currentChatId =
            newChatData.id;

        await loadChats();
    }

    // =========================
    // PDF 업로드
    // =========================

    if (selectedFile) {
        const formData =
            new FormData();

        formData.append(
            "file",
            selectedFile
        );

        formData.append(
            "chat_id",
            currentChatId
        );

        try {
            const uploadResponse =
                await fetch(
                    "/upload-pdf",
                    {
                        method: "POST",
                        body: formData
                    }
                );

            if (!uploadResponse.ok) {
                const errorText =
                    await uploadResponse.text();

                console.error(
                    "PDF 업로드 서버 오류:",
                    errorText
                );

                throw new Error(
                    `PDF 업로드 실패 (${uploadResponse.status})`
                );
            }

            const uploadData =
                await uploadResponse.json();

            if (uploadData.error) {
                throw new Error(
                    uploadData.error
                );
            }

        } catch (error) {
            addMessage(
                "assistant",
                `PDF 업로드 중 오류가 발생했습니다.\n\n${error.message}`
            );

            return;
        }
    }

    // =========================
    // 사용자 메시지
    // =========================

    let displayMessage =
        message;

    if (selectedFile) {
        displayMessage =
            `📄 ${selectedFile.name}\n\n${message}`;
    }

    addMessage(
        "user",
        displayMessage
    );

    messageInput.value = "";
    autoResize();

    // 파일 선택 초기화
    removeSelectedFile();

    sendButton.disabled = true;
    sendButton.textContent = "⋯";

    try {
        let finalMessage =
            message || "첨부한 PDF 내용을 요약해줘.";

        const response =
            await fetch(
                `/chats/${currentChatId}/message`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        message:
                            finalMessage
                    })
                }
            );

        if (!response.ok) {
            throw new Error(
                "서버 오류"
            );
        }

        const assistantMessage =
            addMessage(
                "assistant",
                ""
            );

        const reader =
            response.body.getReader();

        const decoder =
            new TextDecoder();

        let answer = "";

        while (true) {
            const {
                value,
                done
            } = await reader.read();

            if (done) {
                break;
            }

            const chunk =
                decoder.decode(value);

            answer += chunk;

            assistantMessage.innerHTML =
                renderMarkdown(answer);

            scrollToBottom();
        }

        await loadChats();

    } catch (error) {
        addMessage(
            "assistant",
            "오류가 발생했습니다.\n" +
            error.message
        );
    } finally {
        sendButton.disabled = false;
        sendButton.textContent = "➤";
        messageInput.focus();
    }
}


// =========================
// Enter 처리
// =========================

messageInput.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


// =========================
// Textarea 자동 크기
// =========================

messageInput.addEventListener(
    "input",
    autoResize
);


function autoResize() {

    messageInput.style.height =
        "auto";

    messageInput.style.height =
        Math.min(
            messageInput.scrollHeight,
            200
        ) + "px";
}


// =========================
// 스크롤
// =========================

function scrollToBottom() {

    chat.scrollTo({
        top: chat.scrollHeight,
        behavior: "smooth"
    });
}


// =========================
// 새 채팅
// =========================

async function newChat() {

    const response =
        await fetch(
            "/chats",
            {
                method: "POST"
            }
        );


    const newChatData =
        await response.json();


    currentChatId =
        newChatData.id;

    showWelcome();

    await loadChats();

    messageInput.focus();
}


// =========================
// 채팅 목록 불러오기
// =========================

async function loadChats() {

    const response =
        await fetch("/chats");

    const chats =
        await response.json();

    const history =
        document.getElementById(
            "chatHistory"
        );


    history.innerHTML = "";


    for (const chatData of chats) {

        const item =
            document.createElement("div");

        item.className =
            chatData.id === currentChatId
                ? "chat-item active"
                : "chat-item";

        item.dataset.chatId =
            chatData.id;


        const title =
            document.createElement("span");

        title.textContent =
            chatData.title;


        const editButton =
            document.createElement("button");

        editButton.className =
            "edit-chat-btn";

        editButton.textContent =
            "✎";

        editButton.title =
            "제목 수정";

        editButton.onclick =
            (event) => {

                event.stopPropagation();

                openRenameModal(
                    chatData.id,
                    chatData.title
                );
            };


        const deleteButton =
            document.createElement("button");

        deleteButton.className =
            "delete-chat-btn";

        deleteButton.textContent =
            "×";

        deleteButton.title =
            "채팅 삭제";

        deleteButton.onclick =
            (event) => {

                event.stopPropagation();

                deleteChat(chatData.id);
            };


        item.appendChild(title);
        item.appendChild(editButton);
        item.appendChild(deleteButton);

        item.onclick =
            () => {

                loadChat(chatData.id);
            };


        history.appendChild(item);
    }
}


// =========================
// 특정 채팅 불러오기
// =========================

async function loadChat(chatId) {

    currentChatId =
        chatId;


    const response =
        await fetch(
            `/chats/${chatId}`
        );

    const messages =
        await response.json();


    chat.innerHTML = "";


    for (const messageData of messages) {

        addMessage(
            messageData.role,
            messageData.content
        );
    }


    await loadChats();

    scrollToBottom();
}


// =========================
// 채팅 삭제
// =========================

async function deleteChat(chatId) {

    const confirmed =
        confirm("이 채팅을 삭제할까요?");

    if (!confirmed) {
        return;
    }


    const response =
        await fetch(
            `/chats/${chatId}`,
            {
                method: "DELETE"
            }
        );


    if (!response.ok) {

        alert("채팅 삭제에 실패했습니다.");

        return;
    }


    if (currentChatId === chatId) {

        currentChatId = null;

        showWelcome();
    }


    await loadChats();

    messageInput.focus();
}


// =========================
// 채팅 제목 수정
// =========================

function openRenameModal(chatId, currentTitle) {

    renamingChatId =
        chatId;

    renameInput.value =
        currentTitle;

    renameError.textContent =
        "제목을 입력해주세요.";

    renameError.classList.add(
        "hidden"
    );

    renameModal.classList.remove(
        "hidden"
    );

    renameInput.focus();
    renameInput.select();
}


function closeRenameModal() {

    renameModal.classList.add(
        "hidden"
    );

    renamingChatId =
        null;

    renameInput.value =
        "";

    renameError.classList.add(
        "hidden"
    );

    messageInput.focus();
}


async function saveRename() {

    if (renamingChatId === null) {
        return;
    }


    const title =
        renameInput.value.trim();


    if (!title) {

        renameError.textContent =
            "제목을 입력해주세요.";

        renameError.classList.remove(
            "hidden"
        );

        renameInput.focus();

        return;
    }


    renameSaveButton.disabled =
        true;


    try {

        const response =
            await fetch(
                `/chats/${renamingChatId}`,
                {
                    method: "PUT",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        title: title
                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                "제목 수정 실패"
            );
        }


        closeRenameModal();

        await loadChats();

    } catch (error) {

        renameError.textContent =
            "제목 수정에 실패했습니다.";

        renameError.classList.remove(
            "hidden"
        );

    } finally {

        renameSaveButton.disabled =
            false;
    }
}


renameCancelButton.addEventListener(
    "click",
    closeRenameModal
);


renameSaveButton.addEventListener(
    "click",
    saveRename
);


renameInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            saveRename();
        }

        if (event.key === "Escape") {

            closeRenameModal();
        }
    }
);


renameModal.addEventListener(
    "click",
    function(event) {

        if (event.target === renameModal) {

            closeRenameModal();
        }
    }
);


document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Escape" &&
            !renameModal.classList.contains("hidden")
        ) {

            closeRenameModal();
        }
    }
);


// =========================
// 앱 시작
// =========================

loadChats();

// =========================
// PDF 파일 선택
// =========================

fileButton.addEventListener(
    "click",
    function() {

        fileInput.click();

    }
);


fileInput.addEventListener(
    "change",
    function() {

        const file =
            fileInput.files[0];

        if (!file) {
            return;
        }


        if (
            file.type !== "application/pdf" &&
            !file.name.toLowerCase().endsWith(".pdf")
        ) {

            alert("PDF 파일만 첨부할 수 있습니다.");

            fileInput.value = "";

            return;
        }


        selectedFile =
            file;


        showSelectedFile();
    }
);


// =========================
// 선택된 PDF 표시
// =========================

function showSelectedFile() {

    if (!selectedFile) {

        filePreview.innerHTML = "";

        filePreview.classList.add(
            "hidden"
        );

        return;
    }


    filePreview.innerHTML = `

        <div class="file-preview-item">

            <span class="file-preview-icon">
                📄
            </span>

            <span class="file-preview-name">
                ${selectedFile.name}
            </span>

            <button
                class="file-remove-button"
                type="button"
                title="첨부 취소"
            >
                ×
            </button>

        </div>

    `;


    filePreview.classList.remove(
        "hidden"
    );


    const removeButton =
        filePreview.querySelector(
            ".file-remove-button"
        );


    removeButton.onclick =
        removeSelectedFile;
}


// =========================
// PDF 선택 취소
// =========================

function removeSelectedFile() {

    selectedFile =
        null;

    fileInput.value =
        "";

    showSelectedFile();
}
