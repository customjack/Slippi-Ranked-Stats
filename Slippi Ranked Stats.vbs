Set WshShell = CreateObject("WScript.Shell")
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
streamlit = Chr(34) & scriptDir & ".venv\Scripts\streamlit.exe" & Chr(34)
app = Chr(34) & scriptDir & "app.py" & Chr(34)
WshShell.Run streamlit & " run " & app & " --server.headless false --browser.gatherUsageStats false", 0, False
