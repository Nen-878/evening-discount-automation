Option Explicit

Dim shell, fso, baseDir, launcher, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = baseDir

launcher = FindGuiPython(shell, fso)
If launcher = "" Then
    MsgBox "Python GUI launcher (pythonw/pyw) was not found. Install Python 3 or run: python app.py", 16, "Evening Discount"
    WScript.Quit 1
End If

If LCase(fso.GetFileName(launcher)) = "pyw.exe" Then
    command = Quote(launcher) & " -3 " & Quote(baseDir & "\app.pyw")
Else
    command = Quote(launcher) & " " & Quote(baseDir & "\app.pyw")
End If

' Window style 0 + pythonw/pyw = no visible console window.
shell.Run command, 0, False

Function FindGuiPython(sh, fs)
    Dim pathValue, parts, i, candidate, localAppData, roots, root, folder, subFolder
    FindGuiPython = ""

    pathValue = sh.ExpandEnvironmentStrings("%PATH%")
    parts = Split(pathValue, ";")
    For i = 0 To UBound(parts)
        If Len(parts(i)) > 0 Then
            candidate = fs.BuildPath(parts(i), "pyw.exe")
            If fs.FileExists(candidate) Then
                FindGuiPython = candidate
                Exit Function
            End If
            candidate = fs.BuildPath(parts(i), "pythonw.exe")
            If fs.FileExists(candidate) Then
                FindGuiPython = candidate
                Exit Function
            End If
        End If
    Next

    localAppData = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%")
    roots = Array(fs.BuildPath(localAppData, "Python"), fs.BuildPath(fs.BuildPath(localAppData, "Programs"), "Python"))

    For Each root In roots
        If fs.FolderExists(root) Then
            Set folder = fs.GetFolder(root)

            candidate = fs.BuildPath(folder.Path, "pythonw.exe")
            If fs.FileExists(candidate) Then
                FindGuiPython = candidate
                Exit Function
            End If

            For Each subFolder In folder.SubFolders
                candidate = fs.BuildPath(subFolder.Path, "pythonw.exe")
                If fs.FileExists(candidate) Then
                    FindGuiPython = candidate
                    Exit Function
                End If
                candidate = fs.BuildPath(subFolder.Path, "pyw.exe")
                If fs.FileExists(candidate) Then
                    FindGuiPython = candidate
                    Exit Function
                End If
            Next
        End If
    Next
End Function

Function Quote(value)
    Quote = Chr(34) & value & Chr(34)
End Function
