import streamlit as st
import requests
from streamlit_option_menu import option_menu
from share.define.model_enum import RoleName
from datetime import datetime

# --- 設定 API 的基本 URL ---
API_URL = "http://127.0.0.1:8965"

# --- Session State 初始化 ---
st.set_page_config(layout="wide")  # 擴展主畫面寬度

if "token" not in st.session_state:
    st.session_state.token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

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


def handle_status_change(file_id: int):
    """當下拉選單變動時，呼叫 API 更新檔案狀態"""
    # 從 session_state 讀取新選擇的值
    new_value = st.session_state[f"status_{file_id}"]
    is_permanent = new_value == "永久"

    # 準備 API 請求
    body = {"is_permanent": is_permanent}
    response = api_request("patch", f"files/{file_id}/status", json=body)

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
                        st.session_state.token = response.json().get("access_token")
                        st.session_state.user_role = response.json().get("level_name")
                        st.rerun()
                    else:
                        st.error(f"登入失敗: {response.json().get('message', '未知錯誤')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"無法連線到 API: {e}")


def page_file_list():
    st.header("檔案列表")

    # --- 檔案上傳區塊 ---
    with st.expander("上傳新檔案"):
        uploaded_file = st.file_uploader("選擇檔案", label_visibility="collapsed")
        if uploaded_file is not None:
            if st.button("確認上傳"):
                # 使用 multipart/form-data 格式準備檔案
                file_payload = {
                    "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
                }
                # 呼叫後端上傳 API
                response = api_request("post", "files/upload", files=file_payload)

                if response and response.status_code == 200:
                    st.success(f"檔案 '{uploaded_file.name}' 上傳成功！")
                    st.rerun()  # 重新整理頁面以看到新檔案
                elif response:
                    st.error(f"上傳失敗: {response.json().get('message', '未知錯誤')}")

    # --- 檔案列表顯示區塊 ---
    response = api_request("get", "files/list")

    if response and response.status_code == 200:
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
                # 建立標頭
                list_type = [5, 2, 2, 4, 2, 2]
                col1, col2, col3, col4, col5, col6 = st.columns(list_type)
                with col1:
                    st.write("**檔案名稱**")
                with col2:
                    st.write("**檔案大小 (Bytes)**")
                with col3:
                    st.write("**上傳時間**")
                with col4:
                    st.write("**狀態**")
                with col5:
                    st.write("**操作1**")
                with col6:
                    st.write("**操作2**")

                # 循環顯示檔案
                for f in files:
                    # 根據 is_permanent 狀態設定 selectbox 的預設索引
                    del_time_index = 0 if f.get("is_permanent") else 1

                    col1, col2, col3, col4, col5, col6 = st.columns(list_type)
                    with col1:
                        st.write(f["filename"])
                    with col2:
                        st.write(f["size_bytes"])
                    with col3:
                        st.write(f["upload_time"])
                    with col4:
                        st.selectbox(
                            label="",
                            options=["永久", f.get("del_time") or "設定期限"],  # 若無到期日，顯示通用文字
                            index=del_time_index,
                            key=f"status_{f['id']}",
                            on_change=handle_status_change,
                            kwargs={"file_id": f["id"]},
                            label_visibility="collapsed",
                        )
                    with col5:
                        st.button("下載", key=f"download_{f['id']}")
                    with col6:
                        st.button("刪除", key=f"delete_{f['id']}")

    elif response:  # 處理非 200 但非 token 過期的錯誤
        st.error(f"獲取檔案列表失敗: {response.json().get('message', '未知錯誤')}")


def page_user_management():
    st.header("使用者管理")
    st.write("這裡是使用者管理介面。")
    # TODO: Implement user management view


def page_change_password():
    _, center_col, _ = st.columns([2, 4, 2])

    with center_col:
        st.header("更改密碼")
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
                    # 準備呼叫後端 API
                    payload = {
                        "old_password": old_password,
                        "new_password": new_password,
                    }
                    # 假設 API 端點是 /user/change-password
                    response = api_request("post", "userCtrl/change-password", json=payload)

                    if response and response.status_code == 200:
                        st.success("密碼已成功更改！")
                    elif response:
                        st.error(f"更改失敗: {response.json().get('message', '未知錯誤')}")

        if st.button("忘記密碼？"):
            st.info("忘記密碼功能尚在開發中。")


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
