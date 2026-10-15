Set oShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)

oShell.CurrentDirectory = strDir
oShell.Run "pythonw installer.py", 0, False
