# ###########################################################################################################################
# DOCUMENT:https://xiexe.github.io/XSOverlayDocumentation/#/NotificationsAPI
# SOURCE:https://zenn.dev/eeharumt/scraps/95f49a62dd809a
# messageType: int = 0 # 1: ポップアップ通知, 2: メディアプレーヤー情報
# index: int = 0  # メディアプレーヤーでのみ使用され、手首のアイコンを変更する
# timeout: float = 0.5 # 通知インジケータが表示され続ける時間[秒]
# height: float = 175  # 通知インジケータの高さ
# opacity: float = 1  # 通知インジケータの透明度。0.0-1.0の範囲で低いほど透明に
# volume: float = 0.7  # 通知音の大きさ
# audioPath: str = ""  # 通知音ファイルのパス。規定音として"default", "error", "warning"を指定可能。空文字列で通知音なしにできる。
# title: str = ""  # 通知タイトル、リッチテキストフォーマットをサポート。
# content: str = ""  # 通知内容、リッチテキストフォーマットをサポート。省略することで小サイズ通知となる。
# useBase64Icon: bool = False  # TrueにすることでBase64の画像を表示する
# icon: str = ""  # Base64画像イメージまたは画像ファイルパス。規定アイコンとして"default", "error", or "warning"を指定可能
# sourceApp: str = ""  # 通知したアプリ名（デバック用）
# ##########################################################################################################################

import socket
import json
import base64
from os import path as os_path

def XSOverlay(
    endpoint:tuple=("127.0.0.1", 42069), messageType:int=1, index:int=0, timeout:float=2,
    height:float=120.0, opacity:float=1.0, volume:float=0.0, audioPath:str="",
    title:str="", content:str="", useBase64Icon:bool=False, icon:str="default", sourceApp:str=""
) -> int:

    if icon in ["default", "error", "warning"]:
        icon_data = icon
    elif useBase64Icon:
        try:
            with open(icon, "rb") as f:
                icon_data_bytes = f.read()
                icon_data = base64.b64encode(icon_data_bytes).decode("utf-8")
        except Exception:
            icon_data = "default"
    else:
        icon_data = icon

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    data_msg = {
        "messageType": messageType,
        "index": index,
        "timeout":timeout,
        "height": height,
        "opacity": opacity,
        "volume": volume,
        "audioPath": audioPath,
        "title": title,
        "content": content,
        "useBase64Icon": useBase64Icon,
        "icon": icon_data,
        "sourceApp": sourceApp,
    }
    msg_str = json.dumps(data_msg)
    response = sock.sendto(msg_str.encode("utf-8"), endpoint)
    sock.close()
    return response

def xsoverlayForVRCT(content:str="") -> int:
    response = XSOverlay(
        title="VRCT",
        content=content,
        useBase64Icon=True,
        icon=os_path.join(os_path.dirname(__file__), "img", "xsoverlay2.png"),
        sourceApp="VRCT"
    )
    return response

if __name__ == "__main__":
    xsoverlayForVRCT(content="notification test")