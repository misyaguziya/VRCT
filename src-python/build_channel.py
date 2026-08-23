"""
ビルドチャンネル定義

develop/master 間でマージするたびに Aptabase の APP_KEY 取り違えが
発生していたため、差分をこの1行だけに閉じ込める。
develop ブランチではこの値を "beta" のまま維持し、master へマージ/
チェリーピックする際にこの1行だけを "stable" に変更する。
"""
BUILD_CHANNEL = "stable"  # "stable" | "beta"
