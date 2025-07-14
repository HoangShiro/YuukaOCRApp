' YuukaOCR.vbs - Trinh khoi dong im lang tuyet doi
' File nay se chay file launcher.pyw ma khong hien thi bat ky cua so console nao.

' Tao mot doi tuong Shell de thuc thi lenh
Set objShell = CreateObject("WScript.Shell")

' Lay duong dan tuyet doi den thu muc hien tai ma script nay dang chay
' Dieu nay dam bao ung dung luon chay dung, du senpai co chuyen thu muc di dau
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Dinh nghia lenh can chay. Chung ta se chay pythonw.exe voi file launcher.pyw
' dau ngoac kep de xu ly duong dan co dau cach
strCommand = """" & strPath & "\launcher.pyw"""

' Thuc thi lenh
' Tham so 0: Chay cua so mot cach an (khong hien thi)
' Tham so False: Khong doi lenh thuc thi xong moi tiep tuc (chay bat dong bo)
objShell.Run "pythonw.exe " & strCommand, 0, False

' Don dep
Set objShell = Nothing