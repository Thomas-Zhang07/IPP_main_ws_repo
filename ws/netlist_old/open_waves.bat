@echo off
cd /d "%~dp0"
set SALT_LICENSE_SERVER=C:\Users\12966\questa_lic.dat
set QUESTA=D:\altera\questa_fse\win64
start "" "%QUESTA%\vsim.exe" -view waves_old.wlf -do "do view_waves.do"
