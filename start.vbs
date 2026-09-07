Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\Friedrich\Documents\Portfolio\GitHub\Downsort"
On Error Resume Next
sh.Run "pythonw main.pyw", 0, False
If Err.Number <> 0 Then
    Err.Clear
    sh.Run "C:\Users\Friedrich\AppData\Local\Programs\Python\Python312\pythonw.exe main.pyw", 0, False
End If