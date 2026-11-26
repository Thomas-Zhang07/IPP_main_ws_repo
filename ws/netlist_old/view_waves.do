add wave -noupdate -divider {post-0xFD window}
add wave -noupdate -label swap_out   {/tb_top/dut/\inst6|s_swap_out~q\}
add wave -noupdate -label swap_exp   {/tb_top/dut/\inst|s_pulse_out~q\}
add wave -noupdate -label swap_e     {/tb_top/dut/\inst5|s_signal_out~q\}
add wave -noupdate -label current[0] -radix unsigned {/tb_top/dut/\inst8|insts:0:PhaseLine_inst|s_phaseCurrent\}
add wave -noupdate -label current[1] -radix unsigned {/tb_top/dut/\inst8|insts:1:PhaseLine_inst|s_phaseCurrent\}
add wave -noupdate -label current[8] -radix unsigned {/tb_top/dut/\inst8|insts:8:PhaseLine_inst|s_phaseCurrent\}
add wave -noupdate -label DATA0      {/tb_top/data(0)}
add wave -noupdate -label DATA1      {/tb_top/data(1)}
configure wave -timelineunits us
when 3.22ms
wave zoom range 3.20ms 3.44ms
