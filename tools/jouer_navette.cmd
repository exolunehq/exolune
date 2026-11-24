@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lance.ps1" -Build -ModeleVaisseau navette -Camera cockpit -Parcours "%~dp0tests\2026-11-24.txt" -DepartTest 1 -Resolution fenetre
