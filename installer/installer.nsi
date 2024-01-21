!define PRODUCT_VERSION "1.0.0.0"
!define VERSION "1.0.0.0"
VIProductVersion "${PRODUCT_VERSION}"
VIFileVersion "${VERSION}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductName" "VRCT"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "LegalCopyright" "Copyright m's software"
VIAddVersionKey "FileDescription" "Communication tool with translation & transcription for VRChat"

; Modern UI
!include MUI2.nsh
; nsDialogs
!include nsDialogs.nsh
; LogicLib
!include LogicLib.nsh
; FileFunc
!include FileFunc.nsh

!define MUI_ICON "..\img\vrct_logo_mark_black.ico"
!define MUI_UNICON "..\img\vrct_logo_mark_black.ico"

Unicode true
; アプリケーション名
Name "VRCT"
; 作成されるインストーラ
OutFile "VRCT_Setup.exe"

RequestExecutionLevel admin
ShowInstDetails show

; 圧縮メソッド
SetCompressor lzma
; インストールされるディレクトリ
InstallDir "$LOCALAPPDATA\VRCT"
; XPマニフェスト
XPStyle on
; ページ
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
Page custom OptionPage1 OptionPageLeave1
Page custom OptionPage2 OptionPageLeave2
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
; アンインストーラ ページ
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
; 日本語UI
!insertmacro MUI_LANGUAGE "Japanese"
; 引数取得マクロ
!insertmacro GetParameters
!insertmacro GetOptions
; インターフェース 設定
!define MUI_ABORTWARNING
; 変数
Var Checkbox_InstallDocs
Var Checkbox_InstallShortcut
Var Dialog_Options
Var InstallDocs
Var InstallShortcut
Var Label_DescriptionOptions
Var Label_DescriptionComboBox
Var ComboBox_Language
Var Set_Langage
Var DownloadWeight
Var Checkbox_DownloadWeight
Var RadioButton_Download
Var RadioButton_NotDownload

; 初期化時コールバック
Function .onInit
  ; オプション値を初期化します。
  StrCpy $InstallDocs ${BST_CHECKED}
  StrCpy $InstallShortcut ${BST_CHECKED}
  StrCpy $ComboBox_Language "English"
  StrCpy $DownloadWeight ${BST_CHECKED}
FunctionEnd

; オプション ページ 1
Function OptionPage1
  !insertmacro MUI_HEADER_TEXT "オプション" "オプションを設定してください。"
  ; nsDialogsを作成します。
  nsDialogs::Create 1018
  ; 作成されたnsDialogsを変数に代入します。
  Pop $Dialog_Options

  ${If} $Dialog_Options == error
    ; ダイアログの作成に失敗した場合には終了します。
    Abort
  ${EndIf}

  ; ラベルを作成します。
  ${NSD_CreateLabel} 0 0 100% 12u "オプションを選択してください。"
  ; ラベルを変数に代入します。
  Pop $Label_DescriptionOptions

  ${NSD_CreateCheckbox} 0 13u 100% 12u "ドキュメントをインストールする(&D)"
  Pop $Checkbox_InstallDocs

  ${NSD_CreateCheckbox} 0 26u 100% 12u "デスクトップにショートカットを作成(&D)"
  Pop $Checkbox_InstallShortcut
  nsDialogs::Show
FunctionEnd

; オプション ページ 1 退出コールバック
Function OptionPageLeave1
  ${NSD_GetState} $Checkbox_InstallDocs $InstallDocs
  ${NSD_GetState} $Checkbox_InstallShortcut $InstallShortcut
FunctionEnd

; オプション ページ 2
Function OptionPage2
  !insertmacro MUI_HEADER_TEXT "オプション" "初回起動時の設定を設定してください。"
  ; nsDialogsを作成します。
  nsDialogs::Create 1018
  ; 作成されたnsDialogsを変数に代入します。
  Pop $Dialog_Options

  ${If} $Dialog_Options == error
    ; ダイアログの作成に失敗した場合には終了します。
    Abort
  ${EndIf}

  ; ComboBoxを作成します。
  ${NSD_CreateLabel} 0 0u 100% 12u "UIの言語"
  ; ラベルを変数に代入します。
  Pop $Label_DescriptionComboBox

  ${NSD_CreateDropList} 0 15u 100% 12u ""
  Pop $ComboBox_Language

  ${NSD_CreateCheckbox} 0 30u 100% 12u "翻訳モデルのダウンロード(&D)"
  Pop $Checkbox_DownloadWeight

  # ラジオボタンを追加しWEIGHTをDownloadするか選択する
  ${NSD_CreateRadioButton} 0 45u 100% 12u "Download"
  Pop $RadioButton_Download
  ${NSD_CreateRadioButton} 0 60u 100% 12u "Not Download"
  Pop $RadioButton_NotDownload

  ${NSD_CB_AddString} $ComboBox_Language "English"
  ${NSD_CB_AddString} $ComboBox_Language "日本語"
  ${NSD_CB_AddString} $ComboBox_Language "한국어"

  ${NSD_CB_SelectString} $ComboBox_Language "English"
  ${If} $DownloadWeight == ${BST_CHECKED}
    ; チェックが入力済の場合、チェックボックスにチェックを入れます。
    ${NSD_Check} $Checkbox_DownloadWeight
  ${EndIf}
  nsDialogs::Show
FunctionEnd

; オプション ページ 2 退出コールバック
Function OptionPageLeave2
  ${NSD_GetText} $ComboBox_Language $ComboBox_Language
  ${NSD_GetState} $Checkbox_DownloadWeight $DownloadWeight
FunctionEnd

; デフォルト セクション
Section
  ; If VRCT is already running, display a warning message and exit
  StrCpy $1 "VRCT.exe"
  nsProcess::_FindProcess "$1"
  Pop $R1
  ${If} $R1 = 0
    nsExec::ExecToStack "taskkill /IM VRCT.exe"
  ${EndIf}

  ; ディレクトリを削除
  RMDir /r "$INSTDIR"
  ; スタート メニューから削除
  Delete "$SMPROGRAMS\VRCT\VRCT.lnk"
  RMDir "$SMPROGRAMS\VRCT"
  ; デスクトップ ショートカットを削除
  Delete "$DESKTOP\VRCT.lnk"
  ; レジストリ キーを削除
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT"

  ; 出力先を指定します。
  SetOutPath "$INSTDIR"
  ; インストールされるファイル
  File /r "..\dist\VRCT\"

  ${If} $InstallDocs == ${BST_CHECKED}
    ; ドキュメントをインストールする場合
    ; 出力先を指定します。
    SetOutPath "$INSTDIR\docs"
    ; インストールされるファイル
    File "..\README.txt"
  ${EndIf}

  ; アンインストーラを出力
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ${If} $InstallDocs == ${BST_CHECKED}
    ; デスクトップにショートカットを作成
    CreateShortCut "$DESKTOP\VRCT.lnk" "$INSTDIR\VRCT.exe"
  ${EndIf}

  ; ComboBoxの選択値から言語を判定しconfig.jsonを$INSTDIRに作成
  ${If} $ComboBox_Language == "English"
      StrCpy $Set_Langage "en"
  ${ElseIf} $ComboBox_Language == "日本語"
      StrCpy $Set_Langage "ja"
  ${ElseIf} $ComboBox_Language == "한국어"
      StrCpy $Set_Langage "ko"
  ${EndIf}

  ${If} $DownloadWeight == 1
      StrCpy $DownloadWeight "true"
  ${Else}
      StrCpy $DownloadWeight "false"
  ${EndIf}

  StrCpy $1 '{"UI_LANGUAGE": "$Set_Langage", "USE_TRANSLATION_FEATURE": $DownloadWeight}'
  FileOpen $0 "$INSTDIR\config.json" w
  FileWrite $0 $1
  FileClose $0

  ; スタート メニューにショートカットを登録
  CreateDirectory "$SMPROGRAMS\VRCT"
  SetOutPath "$INSTDIR"
  CreateShortcut "$SMPROGRAMS\VRCT\VRCT.lnk" "$INSTDIR\VRCT.exe" ""
  ; レジストリに登録
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT" "DisplayName" "VRCT"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT" "DisplayIcon" '"$INSTDIR\_internal\img\vrct_logo_mark_black.ico"'
SectionEnd

; アンインストーラ
Section Uninstall
  ; If VRCT is already running, display a warning message and exit
  StrCpy $1 "VRCT.exe"
  nsProcess::_FindProcess "$1"
  Pop $R1
  ${If} $R1 = 0
      MessageBox MB_OK|MB_ICONEXCLAMATION "VRCT is still running. Cannot uninstall this software.$\nPlease close VRCT and try again." /SD IDOK
      Abort
  ${EndIf}
  ; ディレクトリを削除
  RMDir /r "$INSTDIR"
  RMDir /r "$LOCALAPPDATA\VRCT"
  ; スタート メニューから削除
  Delete "$SMPROGRAMS\VRCT\VRCT.lnk"
  RMDir "$SMPROGRAMS\VRCT"
  ; デスクトップ ショートカットを削除
  Delete "$DESKTOP\VRCT.lnk"
  ; レジストリ キーを削除
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VRCT"
SectionEnd