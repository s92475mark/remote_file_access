import importlib
from flask import jsonify
from flask_openapi3 import (
    OpenAPI,
    Info,
    Server,
    SecurityScheme,
)  # Import SecurityScheme
from .config_schema import Config
from util.global_variable import global_variable  # <-- 新增
from sqlalchemy import create_engine  # <-- 新增
from sqlalchemy.orm import sessionmaker  # <-- 新增
from flask_jwt_extended import JWTManager
from datetime import timedelta
from jwt.exceptions import ExpiredSignatureError
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from util.register_jobs import scheduler_jobs


class Application:
    def __init__(self, config: Config):
        """
        初始化並設定 Flask 應用程式。
        """
        self.config = config
        global_variable.config = config  # <-- 新增：設定 global_variable.config
        servers = []
        if self.config.OPENAPI.SERVERS:
            server_config_obj = self.config.OPENAPI.SERVERS[0]  # 將其轉換為字典
            server_urls_dict = server_config_obj.model_dump()
            # 為字典中的每一個 URL 值都建立一個 Server 物件
            for url_value in server_urls_dict.values():
                if url_value:
                    servers.append(Server(url=url_value))

        # 使用 flask_openapi3 的方式建立 app
        self.app = OpenAPI(
            "app",
            info=Info(
                title=self.config.OPENAPI.INFO.title,
                version="v1",
                security=[{"BearerAuth": []}],
            ),
            servers=servers,  # 使用我們客製化建立的 server 列表
            # 定義安全方案
            security_schemes={
                "BearerAuth": SecurityScheme(
                    type="http", scheme="bearer", bearerFormat="JWT"
                )
            },
        )

        # --- 資料庫連線設定 ---
        global_variable.database = {}  # 初始化為字典
        for db_name, db_config in self.config.DATABASES.items():
            try:
                engine = create_engine(db_config.SQLALCHEMY_DATABASE_URI)
                SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=engine
                )
                global_variable.database[db_name] = SessionLocal
                print(f"成功設定資料庫連線: {db_name}")
            except Exception as e:
                print(f"設定資料庫連線 {db_name} 失敗: {e}")
        # --- 結束 ---

        # --- 初始化 JWT ---
        # 從我們自己的 Pydantic Config 模型中讀取金鑰，設定到 Flask app 的 config 中
        self.app.config["JWT_SECRET_KEY"] = self.config.JWT.JWT_SECRET_KEY
        self.app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
            minutes=self.config.JWT.JWT_ACCESS_TOKEN_EXPIRES
        )
        # 初始化 JWTManager
        self.jwt = JWTManager(self.app)

        # --- 註冊 JWT 錯誤處理器 ---
        @self.app.errorhandler(ExpiredSignatureError)
        def handle_expired_token_error(e):
            """
            捕捉 JWT token 過期錯誤，並回傳自訂的 JSON 格式。
            """
            return (
                jsonify(
                    {"message": "Token has expired.", "error_code": "TOKEN_EXPIRED"}
                ),
                401,
            )

        # 呼叫內部方法來完成設定
        self._register_blueprints()
        self._register_default_route()
        self._init_scheduler()

    def _init_scheduler(self):
        """初始化並啟動排程器"""
        self.scheduler = BackgroundScheduler(daemon=True)
        for job in scheduler_jobs:
            self.scheduler.add_job(**job)

        self.scheduler.start()
        print(f"排程器已啟動，並已加入 {len(scheduler_jobs)} 個任務。")
        # 註冊應用程式關閉時執行的函式
        atexit.register(lambda: self.scheduler.shutdown())

    def _register_blueprints(self):
        """根據設定檔自動註冊藍圖"""
        for bp_path in self.config.OPENAPI.BLUEPRINTS:
            try:
                module_path, bp_name = bp_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                blueprint = getattr(module, bp_name)

                # --- 新增：檢查藍圖是否已註冊 ---
                if blueprint.name not in self.app.blueprints:
                    # 使用 flask_openapi3 的方法註冊藍圖
                    self.app.register_api(blueprint)
                    print(f"成功註冊藍圖: {bp_path}")
                else:
                    print(f"藍圖 '{bp_path}' 已註冊，跳過重複註冊。")
                # --- 結束 ---

            except (ImportError, AttributeError) as e:
                print(f"無法註冊藍圖 {bp_path}: {e}")

    def _register_default_route(self):
        """註冊一個簡單的根路由"""
        # --- 新增：檢查預設路由是否已註冊 ---
        if "hello_world" not in self.app.view_functions:

            @self.app.route("/")
            def hello_world():
                return "Hello, World!"

        else:
            print(
                "Default route '/' already registered, skipping duplicate registration."
            )
        # --- 結束 ---

    def run(self):
        """從設定檔讀取參數並啟動 Flask 伺服器"""
        print(f"伺服器將在 http://{self.config.FLASK.HOST}:{self.config.FLASK.PORT} 上啟動")
        self.app.run(
            host=self.config.FLASK.HOST,
            port=self.config.FLASK.PORT,
            debug=self.config.FLASK.DEBUG,
        )
