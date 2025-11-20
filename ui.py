import streamlit as st
import requests
from streamlit_option_menu import option_menu
from share.define.model_enum import RoleName
from datetime import datetime
import streamlit.components.v1 as components

# --- 設定 API 的基本 URL ---
API_URL = "http://backend:5042"
# API_URL = "http://127.0.0.1:8965"


# --- Session State 初始化 ---
st.set_page_config(
    layout="wide",
    page_title="雲端分享系統",
    page_icon="./設計一個極簡風格的 favicon，主題.png",
)

if "token" not in st.session_state:
    st.session_state.token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

if "public_domain" not in st.session_state:
    try:
        response = requests.get(
            f"{API_URL.replace('/api', '')}/api/config/public-domain"
        )
        if response.status_code == 200:
            st.session_state.public_domain = response.json().get("public_domain")
        else:
            # 如果後端API取不到，給一個備用值
            st.session_state.public_domain = "http://lf2theo.ddns.net:5566"
    except Exception:
        st.session_state.public_domain = "http://127.0.0.1:8964"

# --- 頁面函式 ---


def api_request(method, endpoint, **kwargs):
    """
    一個包裝函式，用於發送 API 請求並集中處理認證和錯誤。
    """
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        response = requests.request(
            method, f"{API_URL}/{endpoint}", headers=headers, **kwargs
        )

        # 檢查 token 是否過期
        if response.status_code == 401:
            try:
                error_data = response.json()
                if error_data.get("error_code") == "TOKEN_EXPIRED":
                    st.error("連線逾時，請重新登入。")
                    st.session_state.token = None
                    st.session_state.user_role = None
                    st.rerun()
                    return None  # Stop further execution
            except ValueError:  # If response is not JSON
                pass  # Fall through to the generic error display

        return response

    except requests.exceptions.RequestException as e:
        st.error(f"無法連線到 API: {e}")
        return None


def format_bytes(size_bytes):
    """將位元組數轉換為可讀的單位 (B, KB, MB, GB, TB)"""
    if size_bytes is None:
        return "N/A"

    # 確保 size_bytes 是數字
    try:
        size_bytes = float(size_bytes)
    except (ValueError, TypeError):
        return "N/A"

    if size_bytes == 0:
        return "0 Bytes"

    # 定義單位和閾值
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    threshold = 1024.0

    # 計算最適合的單位
    for i in range(len(units)):
        if size_bytes < threshold ** (i + 1):
            return f"{size_bytes / (threshold**i):.2f} {units[i]}"

    # 如果超過 TB，就用最大的單位表示
    return f"{size_bytes / (threshold**(len(units)-1)):.2f} {units[-1]}"


def handle_status_change(safe_filename: str):
    """當下拉選單變動時，呼叫 API 更新檔案狀態"""
    # 從 session_state 讀取新選擇的值
    new_value = st.session_state[f"status_{safe_filename}"]
    is_permanent = new_value == "永久"

    # 準備 API 請求
    body = {"is_permanent": is_permanent}
    response = api_request("patch", f"files/{safe_filename}/status", json=body)

    if response and response.status_code == 200:
        updated_file = response.json()
        is_permanent_after_update = updated_file.get("is_permanent", False)
        expiry_time_str = updated_file.get("del_time")

        if not is_permanent_after_update and expiry_time_str:
            try:
                # 使用 strptime 和指定的格式代碼來解析日期字串
                expiry_time = datetime.strptime(
                    expiry_time_str, "%a, %d %b %Y %H:%M:%S %Z"
                )
                if expiry_time < datetime.now():
                    st.toast("該檔案已過期，將在系統下次清理時自動刪除。", icon="⚠️")
                    return
            except ValueError as e:
                # 如果因任何原因解析失敗，印出錯誤，避免程式崩潰
                print(f"Error parsing date: {e}")

        st.toast("成功更新檔案狀態！", icon="✅")
    else:
        st.toast("更新失敗", icon="❌")


def page_login():
    left, center, right = st.columns([3, 4, 3])

    with center:
        st.header("使用者登入")
        with st.form("login_form"):
            account = st.text_input("帳號")
            password = st.text_input("密碼", type="password")
            submitted = st.form_submit_button("登入")

            if submitted:
                try:
                    response = requests.post(
                        f"{API_URL}/userCtrl/login",
                        json={"account": account, "password": password},
                    )
                    if response.status_code == 200:
                        login_data = response.json()
                        st.session_state.token = login_data.get("access_token")
                        st.session_state.user_role = login_data.get("level_name")
                        st.session_state.user_name = login_data.get("user_name")  # 新增
                        st.rerun()
                    elif response.status_code == 401:
                        st.error(f"帳號密碼錯誤")
                    else:
                        st.error(f"登入失敗: {response.json().get('message', '未知錯誤')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"無法連線到 API: {e}")


def page_file_list():
    # --- 新增：使用 CSS 讓整列垂直置中 ---
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] {
            align-items: center;
        }
        /* 讓上傳元件的按鈕更好看 */
        #upload-button {
            background-color: #0068c9;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        #upload-button:hover {
            background-color: #00509e;
        }
        #file-input {
            display: none;
        }
        #progress-container {
            width: 100%;
            background-color: #f3f3f3;
            border-radius: 5px;
            margin-top: 10px;
        }
        #progress-bar {
            width: 0%;
            height: 20px;
            background-color: #4caf50;
            border-radius: 5px;
            text-align: center;
            line-height: 20px;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- 修改：將標題和搜尋框放在同一列 ---
    col1, col2 = st.columns([8, 2])  # 8:2 的寬度比例，讓搜尋框寬一點

    with col1:
        st.header("檔案列表")

    with col2:
        # --- 檔案名稱搜尋 ---
        if "search_term" not in st.session_state:
            st.session_state.search_term = ""

        search_term_input = st.text_input(
            "搜尋檔案名稱：",
            value=st.session_state.search_term,
            placeholder="檔案搜尋...",
            label_visibility="collapsed",  # 隱藏標籤
        )

    # 如果輸入框的內容與 session_state 中的不同，就更新 session_state 並觸發 rerun
    if search_term_input != st.session_state.search_term:
        st.session_state.search_term = search_term_input
        st.rerun()

    # --- 處理下載請求 ---
    if "download_file" in st.session_state and st.session_state.download_file:
        file_info = st.session_state.download_file
        st.download_button(
            label=f"下載 {file_info['name']}",
            data=file_info["content"],
            file_name=file_info["name"],
            key="final_download_button",
        )
        # 清除 session state，避免重複顯示下載按鈕
        st.session_state.download_file = None

    # --- 檔案上傳區塊 (使用檔案切塊) ---
    with st.expander("上傳新檔案"):
        uploader_html = f"""
        <div id="upload-container">
            <input type="file" id="file-input" />
            <button id="upload-button">選擇檔案</button>
            <div id="status"></div>
            <div id="progress-container" style="display: none;">
                <div id="progress-bar">0%</div>
            </div>
        </div>

        <script>
        window.addEventListener('load', function() {{
            const fileInput = document.getElementById('file-input');
            const uploadButton = document.getElementById('upload-button');
            const statusDiv = document.getElementById('status');
            const progressContainer = document.getElementById('progress-container');
            const progressBar = document.getElementById('progress-bar');
            const api_url = "{API_URL}";
            const token = "{st.session_state.token}";

            // Ensure Streamlit object is available
            function setStreamlitValue(value) {{
                if (window.Streamlit) {{
                    Streamlit.setComponentValue(value);
                }} else {{
                    console.error("Streamlit object not found, retrying in 100ms...");
                    setTimeout(() => setStreamlitValue(value), 100);
                }}
            }}

            uploadButton.onclick = () => fileInput.click();

            fileInput.onchange = async (e) => {{
                const file = e.target.files[0];
                if (!file) return;

                uploadButton.disabled = true;
                uploadButton.innerText = '上傳中...';
                statusDiv.innerText = `準備上傳: ${{file.name}}`;
                progressContainer.style.display = 'block';

                const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
                const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
                const uploadId = `${{file.name}}-${{Date.now()}}`;

                let start = 0;
                let chunkIndex = 0;
                let success = true;

                while (start < file.size) {{
                    const end = Math.min(start + CHUNK_SIZE, file.size);
                    const chunk = file.slice(start, end);

                    const formData = new FormData();
                    formData.append('chunk', chunk, file.name);
                    formData.append('upload_id', uploadId);
                    formData.append('chunk_index', chunkIndex);
                    formData.append('content_type', file.type);

                    try {{
                        const response = await fetch(`${{api_url}}/files/upload_chunk`, {{
                            method: 'POST',
                            body: formData,
                        }});

                        if (!response.ok) {{
                            const error = await response.json();
                            throw new Error(`檔案塊 ${{chunkIndex + 1}} 上傳失敗: ${{error.message || response.statusText}}`);
                        }}

                        chunkIndex++;
                        start += CHUNK_SIZE;
                        const progress = Math.round((chunkIndex / totalChunks) * 100);
                        progressBar.style.width = `${{progress}}%`;
                        progressBar.innerText = `${{progress}}%`;

                    }} catch (error) {{
                        statusDiv.innerText = `錯誤: ${{error.message}}`;
                        statusDiv.style.color = 'red';
                        success = false;
                        break;
                    }}
                }}

                if (success) {{
                    statusDiv.innerText = '所有檔案塊上傳完畢，正在合併檔案...';
                    try {{
                        const completeResponse = await fetch(`${{api_url}}/files/upload_complete`, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${{token}}`
                            }},
                            body: JSON.stringify({{
                                upload_id: uploadId,
                                filename: file.name,
                                total_chunks: totalChunks
                            }})
                        }});

                        if (completeResponse.ok) {{
                            const result = await completeResponse.json();
                            statusDiv.innerText = `成功: '${{file.name}}' 上傳成功！`;
                            statusDiv.style.color = 'green';
                            // 通知 Streamlit 刷新
                            setStreamlitValue({{ "status": "success" }});
                        }} else {{
                            const error = await completeResponse.json();
                            throw new Error(`檔案合併失敗: ${{error.detail || error.message || '未知錯誤'}}`);
                        }}
                    }} catch (error) {{
                        statusDiv.innerText = `錯誤: ${{error.message}}`;
                        statusDiv.style.color = 'red';
                    }}
                }}

                uploadButton.disabled = false;
                uploadButton.innerText = '選擇檔案';
                // Reset file input to allow re-uploading the same file
                fileInput.value = '';
            }};
        }});
        </script>
        """
        upload_status = components.html(uploader_html, height=100)

        if upload_status == {"status": "success"}:
            st.rerun()

    # --- 檔案列表顯示區塊 ---
    # 初始化排序狀態
    if "sort_by" not in st.session_state:
        st.session_state.sort_by = "upload_time"
    if "sort_order" not in st.session_state:
        st.session_state.sort_order = "desc"

    # 修改 API 請求，加入搜尋和排序參數
    params = {
        "filename": st.session_state.search_term,
        "sort_by": st.session_state.sort_by,
        "order": st.session_state.sort_order,
    }
    # print("\033c", end="")
    # print("st.session_state.sort_by", st.session_state.sort_by)
    response = api_request("get", "files/list", params=params)

    if response and response.status_code == 200:
        data = response.json()
        files = data.get("files", [])
        stats = data.get("stats", {})
        limits = data.get("limits", {})

        if not files:
            st.write("沒有找到任何檔案。")
        else:
            with st.container():
                # --- 建立可點擊的標頭 ---
                list_type = [4, 1, 2, 3, 1, 1, 1, 5]  # 調整比例並新增第8欄
                (
                    col1,
                    col2,
                    col3,
                    col4,
                    col5,
                    col6,
                    col7,
                    col8,
                ) = st.columns(list_type)
                current_sort_by = st.session_state.get("sort_by")
                current_order = st.session_state.get("sort_order")

                def create_sort_button(col, column_name, display_text):
                    with col:
                        arrow = ""
                        if current_sort_by == column_name:
                            arrow = "🔼" if current_order == "asc" else "🔽"

                        if st.button(f"**{display_text}** {arrow}"):
                            if (
                                current_sort_by == column_name
                                and current_order == "asc"
                            ):
                                st.session_state.sort_order = "desc"
                            else:
                                st.session_state.sort_by = column_name
                                st.session_state.sort_order = "asc"
                            st.rerun()

                # 建立可排序的標頭
                create_sort_button(col1, "filename", "檔案名稱")
                create_sort_button(col2, "size_bytes", "檔案大小")
                create_sort_button(col3, "upload_time", "上傳時間")

                # 建立不可排序的標頭 (使用 disabled button 以統一外觀)
                with col4:
                    st.button("**狀態**", disabled=True)
                with col5:
                    pass
                with col6:
                    pass
                with col7:
                    pass

                # 循環顯示檔案
                for f in files:
                    del_time_index = 0 if f.get("is_permanent") else 1

                    (col1, col2, col3, col4, col5, col6, col7, col8) = st.columns(
                        list_type
                    )
                    share_token = f.get("share_token")
                    with col1:
                        st.write(f["filename"])
                    with col2:
                        st.write(format_bytes(f["size_bytes"]))
                    with col3:
                        st.write(f["upload_time"])
                    with col4:
                        st.selectbox(
                            label="狀態",
                            options=["永久", f.get("del_time") or "設定期限"],
                            index=del_time_index,
                            key=f"status_{f['safe_filename']}",
                            on_change=handle_status_change,
                            kwargs={"safe_filename": f["safe_filename"]},
                            label_visibility="collapsed",
                        )
                    with col5:
                        placeholder = st.empty()
                        download_url = f["download_url"]
                        placeholder.markdown(
                            f"""
                            <div style="text-align:center; padding-top:0px;">
                                <a href="{download_url}" download="{f["filename"]}">下載</a>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col6:
                        if st.button("刪除", key=f"delete_{f['safe_filename']}"):
                            response = api_request(
                                "delete", f"files/{f['safe_filename']}"
                            )
                            if response and response.status_code == 200:
                                st.toast("檔案刪除成功！", icon="✅")
                                st.rerun()
                            elif response:
                                st.error(
                                    f"刪除失敗: {response.json().get('message', '未知錯誤')}"
                                )
                    with col7:
                        if share_token:
                            if st.button(
                                "移除分享", key=f"remove_share_{f['safe_filename']}"
                            ):
                                response = api_request(
                                    "delete", f"files/{f['safe_filename']}/share"
                                )
                                if response and response.status_code == 200:
                                    st.toast("分享已移除！", icon="🗑️")
                                    st.rerun()
                                else:
                                    st.error("移除失敗")
                        else:
                            if st.button(
                                "建立分享", key=f"create_share_{f['safe_filename']}"
                            ):
                                response = api_request(
                                    "post", f"files/{f['safe_filename']}/share"
                                )
                                if response and response.status_code == 200:
                                    st.toast("分享連結已產生！", icon="✅")
                                    st.rerun()
                                else:
                                    st.error("建立失敗")
                    with col8:
                        if share_token:
                            public_domain = st.session_state.get("public_domain", "")
                            full_share_url = (
                                f"{public_domain}/api/files/shared/{share_token}"
                            )
                            st.text_input(
                                "分享連結",
                                full_share_url,
                                key=f"link_{f['safe_filename']}",
                                disabled=True,
                                label_visibility="collapsed",
                            )

            # --- 在列表下方顯示統計資訊 (靠右) ---
            st.divider()
            st.markdown(
                f"""
                <div style="text-align: right;">
                    檔案數量: {stats.get('file_count', 0)} / {limits.get('file_limit', 'N/A')}<br>
                    永久檔案: {stats.get('permanent_file_count', 0)} / {limits.get('permanent_file_limit', 'N/A')}
                </div>
                """,
                unsafe_allow_html=True,
            )

    elif response:  # 處理非 200 但非 token 過期的錯誤
        st.error(f"獲取檔案列表失敗: {response.json().get('message', '未知錯誤')}")


def page_user_management():
    st.header("使用者管理")

    # --- 彈出式表單：用於建立新使用者 ---
    with st.expander("建立新使用者", expanded=False):
        with st.form("new_user_form", clear_on_submit=True):
            new_account = st.text_input("新帳號")
            new_password = st.text_input("新密碼", type="password")

            submitted = st.form_submit_button("確認新增")
            if submitted:
                if not new_account or not new_password:
                    st.warning("帳號和密碼為必填欄位。")
                else:
                    # 步驟 1: 呼叫 API 檢查帳號是否已存在
                    check_params = {"account": new_account}
                    check_response = api_request(
                        "get", "userCtrl/accountCheck", params=check_params
                    )

                    # 步驟 2: 根據檢查結果，決定是否繼續建立使用者
                    if check_response and check_response.status_code == 200:
                        # 帳號合法，繼續建立使用者
                        payload = {
                            "account": new_account,
                            "password": new_password,
                            "name": new_account,  # 暫用 account 替代
                            "storage_path": new_account,  # 暫用 account 替代
                        }
                        create_response = api_request(
                            "post", "userCtrl/createUser", json=payload
                        )

                        if create_response and create_response.status_code == 200:
                            st.success(f"已成功建立使用者：{new_account}")
                            st.rerun()
                        elif create_response:
                            st.error(
                                f"建立失敗: {create_response.json().get('message', '未知錯誤')}"
                            )

                    elif check_response and check_response.status_code == 409:
                        # 帳號已存在
                        st.error(f"帳號 '{new_account}' 已被使用，請更換一個。")
                    else:
                        # 其他可能的錯誤
                        st.error("帳號驗證失敗，請稍後再試。")

    st.divider()

    # --- 現有使用者列表 ---
    st.subheader("現有使用者列表")
    response = api_request("get", "userCtrl/list-all")

    if response and response.status_code == 200:
        users = response.json().get("users", [])
        if not users:
            st.info("目前沒有任何使用者。")
        else:
            # 建立標頭
            cols = st.columns([2, 2, 2, 2, 2, 2])
            headers = ["帳號", "名稱", "角色", "檔案數量", "永久檔案", "空間用量"]
            for col, header in zip(cols, headers):
                col.write(f"**{header}**")

            # 循環顯示使用者
            for user in users:
                # 格式化空間使用量
                storage_usage_bytes = user.get("total_file_size", 0)
                storage_display = format_bytes(storage_usage_bytes)

                cols = st.columns([2, 2, 2, 2, 2, 2])
                cols[0].write(user.get("account"))
                cols[1].write(user.get("name"))
                cols[2].write(user.get("role_name"))
                cols[3].write(
                    f"{user.get('total_file', 0)} / {user.get('file_limit', 'N/A')}"
                )
                cols[4].write(
                    f"{user.get('p_total_file', 0)} / {user.get('permanent_file_limit', 'N/A')}"
                )
                cols[5].write(storage_display)

    else:
        st.error("無法獲取使用者列表。")


def page_change_password():
    st.header("使用者設定")

    # --- 區塊一：使用者資訊 ---
    st.subheader("使用者資訊")

    with st.spinner("正在獲取使用者資訊..."):
        response = api_request("get", "userCtrl/info")

    if response and response.status_code == 200:
        user_info = response.json()

        # 格式化空間使用量
        storage_usage_bytes = user_info.get("storage_usage", 0)
        storage_display = format_bytes(storage_usage_bytes)

        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "使用者名稱", value=user_info.get("user_name", "N/A"), disabled=True
            )
            st.text_input(
                "總檔案數量",
                value=f"{user_info.get('file_count', 0)} / {user_info.get('file_limit', 'N/A')}",
                disabled=True,
            )

        with col2:
            st.text_input("帳號", value=user_info.get("account", "N/A"), disabled=True)
            st.text_input(
                "永久檔案數量",
                value=f"{user_info.get('permanent_file_count', 0)} / {user_info.get('permanent_file_limit', 'N/A')}",
                disabled=True,
            )

        st.text_input("總空間使用量", value=storage_display, disabled=True)

    else:
        st.error("無法獲取使用者資訊。")

    st.divider()  # 分隔線

    # --- 區塊二：更改密碼 ---
    st.subheader("更改密碼")
    _, center_col, _ = st.columns([2, 4, 2])  # 讓表單置中

    with center_col:
        with st.form("change_password_form", clear_on_submit=True):
            old_password = st.text_input("舊密碼", type="password")
            new_password = st.text_input("新密碼", type="password")
            confirm_password = st.text_input("確認新密碼", type="password")

            submitted = st.form_submit_button("確認更改")

            if submitted:
                if not old_password or not new_password or not confirm_password:
                    st.warning("所有欄位皆為必填。")
                elif new_password != confirm_password:
                    st.error("新密碼與確認密碼不相符！")
                else:
                    payload = {
                        "old_password": old_password,
                        "new_password": new_password,
                    }
                    response = api_request(
                        "post", "userCtrl/change-password", json=payload
                    )

                    if response and response.status_code == 200:
                        st.success("密碼已成功更改！請使用新密碼重新登入。")
                        # 清除 session state 並強制重新登入
                        st.session_state.token = None
                        st.session_state.user_role = None
                        st.session_state.user_name = None
                        st.rerun()
                    elif response:
                        st.error(f"更改失敗: {response.json().get('message', '未知錯誤')}")

        if st.button("忘記密碼？"):
            st.info("忘記密碼功能尚在開發中。")


# --- 主應用程式 ---
left, center, right = st.columns([3, 4, 3])

title_show: bool = False

with center:
    if title_show:
        st.title("**檔案遠端存取系統**")
        st.markdown(
            """<marquee behavior="scroll" direction="left"> 夜安"</marquee>""",
            unsafe_allow_html=True,
        )

if st.session_state.token is None:
    page_login()
else:
    with st.sidebar:
        if st.session_state.user_name:
            st.markdown(f"### 您好，{st.session_state.user_name}")
            st.divider()

        if st.session_state.user_role in (
            [RoleName.superadmin.value, RoleName.admin.value]
        ):
            selected = option_menu(
                "主選單",
                ["檔案列表", "使用者管理", "使用者設定", "登出"],
                icons=["list-task", "people", "key", "box-arrow-right"],
                menu_icon="cast",
                default_index=0,
            )
        else:
            selected = option_menu(
                "主選單",
                ["檔案列表", "使用者設定", "登出"],
                icons=["list-task", "people", "key", "box-arrow-right"],
                menu_icon="cast",
                default_index=0,
            )

    if selected == "檔案列表":
        page_file_list()
    elif selected == "使用者管理":
        page_user_management()
    elif selected == "使用者設定":
        page_change_password()
    elif selected == "登出":
        st.session_state.token = None
        st.rerun()
