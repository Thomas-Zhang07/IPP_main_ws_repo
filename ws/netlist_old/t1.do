add wave -noupdate -label swap_out "/tb_top/dut/\inst6|s_swap_out~q\\"
add wave -noupdate -label swap_exp "/tb_top/dut/\inst|s_pulse_out~q\\"
add wave -noupdate -label swap_e "/tb_top/dut/\inst5|s_signal_out~q\\"
find signals *s_phaseCurrent*
quit -f
