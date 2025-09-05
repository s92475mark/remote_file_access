import streamlit as st
import requests
from streamlit_option_menu import option_menu
from share.define.model_enum import RoleName

# --- 設定 API 的基本 URL ---
API_URL = "http://127.0.0.1:8965"

# --- Session State 初始化 ---
st.set_page_config(layout="wide")  # 擴展主畫面寬度

if "token" not in st.session_state:
    st.session_state.token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# --- 頁面函式 ---


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
                        st.session_state.token = response.json().get("access_token")
                        st.session_state.user_role = response.json().get("level_name")
                        st.rerun()
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
                with st.container(
                    border=True,
                    height="stretch",
                    horizontal_alignment="center",
                    width="stretch",
                ):
                    # Create a header row
                    list_type = [5, 2, 2, 2, 4, 2, 2]
                    col1, col2, col3, col4, col5, col6, col7 = st.columns(list_type)
                    with col1:
                        st.write("**檔案名稱**")
                    with col2:
                        st.write("**檔案大小 (Bytes)**")
                    with col3:
                        st.write("**上傳時間**")
                    with col4:
                        st.write("**移除時間**")
                    with col5:
                        st.write("**狀態**")
                    with col6:
                        st.write("**操作1**")
                    with col7:
                        st.write("**操作2**")

                    # Loop through the files and create a row for each
                    for f in files:
                        del_time = f["del_time"]
                        col1, col2, col3, col4, col5, col6, col7 = st.columns(list_type)
                        with col1:
                            st.write(f["filename"])
                        with col2:
                            st.write(f["size_bytes"])
                        with col3:
                            st.write(f["upload_time"])
                        with col4:
                            st.write(f["del_time"])
                        with col5:
                            st.selectbox(
                                label="",
                                options=["永久", f"{del_time}"],
                                key=f"status_{f['id']}",
                                label_visibility="collapsed",
                            )
                        with col6:
                            st.button("下載", key=f"download_{f['id']}")
                        with col7:
                            st.button("刪除", key=f"delete_{f['id']}")

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
left, center, right = st.columns([3, 4, 3])

with center:
    st.title("**檔案遠端存取系統**")

if st.session_state.token is None:
    page_login()
else:
    with st.sidebar:
        if st.session_state.user_role in (
            [RoleName.superadmin.value, RoleName.admin.value]
        ):
            selected = option_menu(
                "主選單",
                ["檔案列表", "使用者管理", "更改密碼", "登出"],
                icons=["list-task", "people", "key", "box-arrow-right"],
                menu_icon="cast",
                default_index=0,
            )
        else:
            selected = option_menu(
                "主選單",
                ["檔案列表", "更改密碼", "登出"],
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
        st.rerun()
