Set oShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)

If fso.FolderExists(strDir & "\aegis") Then
    oShell.CurrentDirectory = strDir & "\aegis"
Else
    oShell.CurrentDirectory = strDir
End If

oShell.Run "pythonw installer.py", 0, False
