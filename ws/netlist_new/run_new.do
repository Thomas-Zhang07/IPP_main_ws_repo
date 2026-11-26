vcd file waves_new.vcd
vcd add "/tb_top/dut/\\inst6|s_swap_out~q\\"
vcd add "/tb_top/dut/\\inst|s_pulse_out~q\\"
vcd add "/tb_top/dut/\\inst5|s_signal_out~q\\"
vcd add "/tb_top/dut/\\inst8|insts:0:PhaseLine_inst|s_phaseCurrent\\"
vcd add "/tb_top/dut/\\inst8|insts:1:PhaseLine_inst|s_phaseCurrent\\"
vcd add "/tb_top/dut/\\inst8|insts:8:PhaseLine_inst|s_phaseCurrent\\"
vcd add "/tb_top/dut/\\inst8|insts:0:PhaseLine_inst|s_phasePrev\\"
vcd add "/tb_top/data(0)"
vcd add "/tb_top/data(1)"
run 4 ms
vcd flush
quit -f
