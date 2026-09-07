Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
On Error Resume Next
sh.Run "pythonw main.pyw", 0, False
If Err.Number <> 0 Then
    Err.Clear
    sh.Run "python main.pyw", 0, False
End If