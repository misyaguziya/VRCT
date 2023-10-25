# アンインストーラ
Section "Uninstall"
  # アンインストーラを削除
  # Delete "$INSTDIR\Uninstall.exe"
  # ファイルを削除
  # Delete "$INSTDIR\VRCT.exe"
  # ディレクトリを削除
  RMDir /r "$INSTDIR"
  # スタート メニューから削除
  Delete "$SMPROGRAMS\VRCT\VRCT.lnk"
  RMDir "$SMPROGRAMS\VRCT"
  # デスクトップ ショートカットを削除
  Delete "$DESKTOP\VRCT.lnk"
  # レジストリ キーを削除
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT"
SectionEnd