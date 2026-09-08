Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' 1) Preferred: bundled portable exe (no Python/customtkinter needed)
exe = dir & "dist\Downsort.exe"
If fso.FileExists(exe) Then
    sh.Run Chr(34) & exe & Chr(34), 0, False
Else
    ' 2) Fallback: run main.pyw with the known-good system Python 3.12 pythonw
    main = dir & "main.pyw"
    sysPy = "C:\Users\Friedrich\AppData\Local\Programs\Python\Python312\pythonw.exe"
    sh.Environment("PROCESS")("PYTHONPATH") = ""
    If fso.FileExists(sysPy) Then
        sh.Run Chr(34) & sysPy & Chr(34) & " " & Chr(34) & main & Chr(34), 0, False
    Else
        sh.Run "pythonw " & Chr(34) & main & Chr(34), 0, False
    End If
End If