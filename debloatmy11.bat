@echo off
REM ===============================================
REM   Samsoft OS NT 11 Branding Script
REM   Makes Windows appear as "Samsoft OS NT 11"
REM ===============================================

color 0a
title Samsoft OS NT 11 Boot

echo ===============================================
echo   SAMSOFT OS NT 11
echo   Build 2025.09  |  DebloatMy11 Core
echo ===============================================
echo [BOOT] Kernel: Windows NT 11.x
echo [PATCH] Explorer: Samsoft Shell
echo [PATCH] Telemetry: Disabled
echo [PATCH] Updates: Samsoft Update Manager
echo [STATE] System Ready - Kyoto Deployment Mode
echo.

:: Change the product name (what winver/systeminfo shows)
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v ProductName /t REG_SZ /d "Samsoft OS NT 11" /f

:: Change registered owner
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v RegisteredOwner /t REG_SZ /d "Samsoft.Glaceon" /f

:: Optional: change edition ID string too
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v EditionID /t REG_SZ /d "SamsoftNT11" /f

:: Optional: change display version
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v DisplayVersion /t REG_SZ /d "Samsoft Build 2025.09" /f

echo [INFO] Branding applied. Restart or run WINVER to see "Samsoft OS NT 11".
pause
