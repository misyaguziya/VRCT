# Modern UI
!include MUI2.nsh
# nsDialogs
!include nsDialogs.nsh
# LogicLib
!include LogicLib.nsh

Unicode True
# アプリケーション名
Name "VRCT Setup"
# 作成されるインストーラ
OutFile "VRCT_Setup.exe"

RequestExecutionLevel admin
ShowInstDetails show

# 圧縮メソッド
SetCompressor lzma
# インストールされるディレクトリ
InstallDir "$PROGRAMFILES\VRCT"
# XPマニフェスト
XPStyle on
# ページ
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
Page custom OptionPage OptionPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
# アンインストーラ ページ
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
# 日本語UI
!insertmacro MUI_LANGUAGE "Japanese"
# インターフェース 設定
!define MUI_ABORTWARNING
# 変数
Var Checkbox_InstallDocs
Var Checkbox_InstallShortcut
Var Dialog_Options
Var InstallDocs
Var InstallShortcut
Var Label_DescriptionOptions

# 初期化時コールバック
Function .onInit
  # オプション値を初期化します。
  StrCpy $InstallDocs ${BST_CHECKED}
  StrCpy $InstallShortcut ${BST_CHECKED}
FunctionEnd

# オプション ページ
Function OptionPage
  # nsDialogsを作成します。
  nsDialogs::Create 1018
  # 作成されたnsDialogsを変数に代入します。
  Pop $Dialog_Options

  ${If} $Dialog_Options == error
    # ダイアログの作成に失敗した場合には終了します。
    Abort
  ${EndIf}

  # ラベルを作成します。
  ${NSD_CreateLabel} 0 0 100% 12u "オプションを選択してください。"
  # ラベルを変数に代入します。
  Pop $Label_DescriptionOptions

  ${NSD_CreateCheckbox} 0 13u 100% 12u "ドキュメントをインストールする(&D)"
  Pop $Checkbox_InstallDocs

  ${NSD_CreateCheckbox} 0 26u 100% 12u "デスクトップにショートカットを作成(&D)"
  Pop $Checkbox_InstallShortcut

  ${If} $InstallDocs == ${BST_CHECKED}
    # チェックが入力済の場合、チェックボックスにチェックを入れます。
    ${NSD_Check} $Checkbox_InstallDocs
  ${EndIf}
  ${If} $InstallShortcut == ${BST_CHECKED}
    # チェックが入力済の場合、チェックボックスにチェックを入れます。
    ${NSD_Check} $Checkbox_InstallShortcut
  ${EndIf}
  nsDialogs::Show
FunctionEnd

# オプション ページ退出コールバック
Function OptionPageLeave
  ${NSD_GetState} $Checkbox_InstallDocs $InstallDocs
  ${NSD_GetState} $Checkbox_InstallShortcut $InstallShortcut
FunctionEnd

# デフォルト セクション
Section
  # 出力先を指定します。
  SetOutPath "$INSTDIR"
  # インストールされるファイル
  File /r "..\dist\VRCT\"

  ${If} $InstallDocs == ${BST_CHECKED}
    # ドキュメントをインストールする場合
    # 出力先を指定します。
    SetOutPath "$INSTDIR\docs"
    # インストールされるファイル
    File "..\dist\README.txt"
  ${EndIf}

  # アンインストーラを出力
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ${If} $InstallDocs == ${BST_CHECKED}
    # デスクトップにショートカットを作成
    CreateShortCut "$DESKTOP\VRCT.lnk" "$INSTDIR\VRCT.exe"
  ${EndIf}

  # スタート メニューにショートカットを登録
  CreateDirectory "$SMPROGRAMS\VRCT"
  SetOutPath "$INSTDIR"
  CreateShortcut "$SMPROGRAMS\VRCT\VRCT.lnk" "$INSTDIR\VRCT.exe" ""
  # レジストリに登録
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT" "DisplayName" "VRCT"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT" "DisplayIcon" '"$INSTDIR\_internal\img\vrct_logo_mark_black.ico"'
SectionEnd

# アンインストーラ
!include Uninstall.nsi
