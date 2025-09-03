
import streamlit as st
import requests
from streamlit_option_menu import option_menu

# --- 設定 API 的基本 URL ---
API_URL = "http://127.0.0.1:8965"

# --- Session State 初始化 ---
if 'token' not in st.session_state:
    st.session_state.token = None

# --- 頁面函式 ---

def page_login():
    st.header("使用者登入")
    with st.form("login_form"):
        account = st.text_input("帳號")
        password = st.text_input("密碼", type="password")
        submitted = st.form_submit_button("登入")

        if submitted:
            try:
                response = requests.post(
                    f"{API_URL}/userCtrl/login",
                    json={"account": account, "password": password}
                )
                if response.status_code == 200:
                    st.session_state.token = response.json().get("access_token")
                    st.success("登入成功！請重新整理頁面。")
                else:
                    st.error(f"登入失敗: {response.json().get('message', '未知錯誤')}")
            except requests.exceptions.RequestException as e:
                st.error(f"無法連線到 API: {e}")

def page_file_list():
    st.header("檔案列表")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        response = requests.get(f"{API_URL}/files/list", headers=headers)
        if response.status_code == 200:
            files = response.json().get("files", [])
            if not files:
                st.write("沒有找到任何檔案。")
            else:
                # Create a list of dictionaries for the dataframe
                file_data = []
                for f in files:
                    file_data.append({
                        "ID": f["id"],
                        "檔案名稱": f["filename"],
                        "檔案大小 (Bytes)": f["size_bytes"],
                        "上傳時間": f["upload_time"],
                    })
                st.dataframe(file_data)

                # Add download and delete buttons
                for f in files:
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.button(f"下載 {f['filename']}", key=f"download_{f['id']}")
                    with col2:
                        st.button(f"刪除 {f['filename']}", key=f"delete_{f['id']}")

        else:
            st.error(f"獲取檔案列表失敗: {response.json().get('message', '未知錯誤')}")
    except requests.exceptions.RequestException as e:
        st.error(f"無法連線到 API: {e}")

def page_user_management():
    st.header("使用者管理")
    st.write("這裡是使用者管理介面。")
    # TODO: Implement user management view

def page_change_password():
    st.header("更改密碼")
    st.write("這裡是更改密碼介面。")
    # TODO: Implement change password view

# --- 主應用程式 ---
st.title("檔案遠端存取系統")

if st.session_state.token is None:
    page_login()
else:
    with st.sidebar:
        selected = option_menu(
            "主選單",
            ["檔案列表", "使用者管理", "更改密碼", "登出"],
            icons=["list-task", "people", "key", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
        )

    if selected == "檔案列表":
        page_file_list()
    elif selected == "使用者管理":
        page_user_management()
    elif selected == "更改密碼":
        page_change_password()
    elif selected == "登出":
        st.session_state.token = None
        # No rerun needed, the script will rerun automatically on the next interaction
