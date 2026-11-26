onerror {quit -f}
add wave -noupdate -label swap_out "/waves_old/tb_top/dut/\\inst6|s_swap_out~q\\"
add wave -noupdate -label swap_exp "/waves_old/tb_top/dut/\\inst|s_pulse_out~q\\"
add wave -noupdate -label swap_e "/waves_old/tb_top/dut/\\inst5|s_signal_out~q\\"
quit -f
