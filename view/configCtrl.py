"""提供前端所需的後端設定值"""

from flask_openapi3 import APIBlueprint
from util.global_variable import global_variable

config_api = APIBlueprint("config_api", __name__, url_prefix="/config")


@config_api.get("/public-domain")
def get_public_domain():
    """獲取應用程式的公開網域設定"""
    domain = global_variable.config.APP.PUBLIC_DOMAIN
    return {"public_domain": domain}
