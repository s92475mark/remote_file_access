import click
import os
import toml
from typing import Union
from util.createapp import Application
from util.config_schema import Config

# --- 全域變數 ---
CONFIG: Union[Config, None] = None


@click.group()
def cli():
    pass


@cli.command()
@click.argument("config_name", required=False)
def run(config_name):
    """根據設定檔來執行 flask server"""
    global CONFIG

    if config_name is None:
        file_name = "config.toml"
    else:
        file_name = f"config.{config_name}.toml"
    config_path = os.path.join("config", file_name)

    if not os.path.exists(config_path):
        click.echo(f"錯誤：設定檔 '{config_path}' 不存在！")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = toml.load(f)

    CONFIG = Config(**config_data)

    # --- 主要修改處 ---
    # 1. 建立 Application 的實例 (instance)
    application = Application(config=CONFIG)
    # 2. 呼叫實例中的 run 方法來啟動伺服器
    application.run()


@cli.command()
@click.argument("config_name", required=False)
def configupdate(config_name):
    """
    檢查設定檔是否存在。
    不存在則建立；若存在，則根據 schema 補全缺少的欄位。
    """
    config_dir = "config"
    os.makedirs(config_dir, exist_ok=True)

    if config_name is None:
        file_name = "config.toml"
    else:
        file_name = f"config.{config_name}.toml"

    config_path = os.path.join(config_dir, file_name)

    if not os.path.exists(config_path):
        default_config = Config()
        config_data = default_config.model_dump()
        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)
        click.echo(f"'{config_path}' 不存在，已根據 schema 建立預設設定。")
    else:
        click.echo(f"'{config_path}' 已存在，正在檢查並更新...")

        with open(config_path, "r", encoding="utf-8") as f:
            existing_data = toml.load(f)

        updated_config = Config(**existing_data)
        updated_data = updated_config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(updated_data, f)

        click.echo(f"'{config_path}' 已更新完成。")





if __name__ == "__main__":
    cli()
