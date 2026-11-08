#Persistent
#NoTrayIcon
#SingleInstance Force

#Include %A_ScriptDir%\UDF.ahk

Gui, +LastFound
hWnd := WinExist()
Gui, Show, Hide, AmazingBinderAHKReceiver

addChatMessageEx("0x33CC33", "[Биндер] Гибридный биндер успешно запущен и подключен к игре!")

OnMessage(0x4A, "ReceiveData")
return

ReceiveData(wParam, lParam) {
    StringAddress := NumGet(lParam + 2*A_PtrSize)
    CopyData := StrGet(StringAddress, "CP1251")
    
    Pos := InStr(CopyData, "|")
    if (Pos) {
        Action := SubStr(CopyData, 1, Pos - 1)
        Param := SubStr(CopyData, Pos + 1)
        
        if (!checkHandles())
            return 1

        if (Action == "chat") {
            sendChat(Param)
        }
        else if (Action == "local") {
            addChatMessageEx("0x33CC33", Param)
        }
    }
    return 1
}