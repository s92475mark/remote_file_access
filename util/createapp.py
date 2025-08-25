import importlib
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


class Application:
    def __init__(self, config: Config):
        """
        初始化並設定 Flask 應用程式。
        """
        self.config = config
        global_variable.config = config  # <-- 新增：設定 global_variable.config

        # 使用 flask_openapi3 的方式建立 app
        self.app = OpenAPI(
            "app",
            info=Info(
                title=self.config.OPENAPI.INFO.title,
                version="v1",
                security=[{"BearerAuth": []}],
            ),
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

        # 呼叫內部方法來完成設定
        self._register_blueprints()
        self._register_default_route()

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
