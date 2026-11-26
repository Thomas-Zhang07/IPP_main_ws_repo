@echo off
rem Open the pre-fix netlist simulation in the Questa GUI.
rem Press "Run -All" (F9) afterwards; the frame ends around 3.2 ms.
cd /d "%~dp0"
set SALT_LICENSE_SERVER=C:\Users\12966\questa_lic.dat
set QUESTA=D:\altera\questa_fse\win64
start "" "%QUESTA%\vsim.exe" -gui -t 1ps ^
  -L altera -L cycloneive -L altera_mf -L altera_lnsim ^
  -voptargs="+acc" work.tb_top -do "do gui_waves.do"
