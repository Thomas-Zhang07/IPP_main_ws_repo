16x16 超声阵列驱动 —— 仿真包
================================

目录结构
--------
fpga_code/            Quartus 工程、VHDL 源码、sim/ testbench 与运行脚本
demo/                 sim/gen_assets.py 依赖的 Python 模块
                      (acoustics.py / protocol.py / emitters.py / requirements.txt)
README_TEAMMATE.txt   本文件


先决条件
--------
- Quartus Prime Lite 25.1（或兼容版本）
- Questa Altera Starter FPGA Edition 2025.2（需要 altera / cycloneive 预编译库）
- Python 3.10+；RTL 套件还需要 numpy 和 pyserial：
      pip install -r demo/requirements.txt


先改路径（重要）
----------------
fpga_code/sim/run_sim.ps1 和 run_top_sim.ps1 里这两行是硬编码的，
按你自己的环境修改：

    $env:SALT_LICENSE_SERVER = 'C:\Users\12966\questa_lic.dat'
    $questa = 'D:\altera\questa_fse\win64'


1) 顶层后仿真（整个模块，对 Quartus 网表）
-------------------------------------------
    cd fpga_code
    .\sim\run_top_sim.ps1

- 被测对象：simulation/questa/QuadrupleBuffer.vho
  （Quartus Prime Lite 25.1 生成，已包含 PulseExpander 修复）
- 运行 4 ms，成功输出：PASS tb_top
- 这个流程不需要 Python

注意：.vho 是构建产物，不在 git 里。如果改了 src/*.vhd，
需要先在 Quartus 里 Start Compilation，重新生成它。


2) RTL 套件（8 个 testbench，不需要网表）
-----------------------------------------
    cd fpga_code
    .\sim\run_sim.ps1

- 会先调用 sim/gen_assets.py 生成相位表和 demo 帧
  （所以需要同级 demo/ 目录，以及 numpy、pyserial）
- 然后编译 src/*.vhd + sim/tb_*.vhd 并运行 8 个测试
- 成功输出：ALL TESTS PASSED


主要 testbench
--------------
sim/tb_top.vhd           整个 QuadrupleBuffer 顶层，对 .vho 网表跑后仿真
sim/tb_glue.vhd          UARTReader -> RSSFilter_1 -> Distribute ->
                         PulseExpander -> LatchBuffer -> AllChannels 集成测试
                         （PulseExpander 毛刺 bug 的回归测试：
                           修复前 FAIL，修复后 PASS）
sim/tb_distribute.vhd    协议解码单元测试
sim/tb_phaseline.vhd     相位精度单元测试
sim/tb_allchannels.vhd   通道阵列单元测试
sim/tb_music_player.vhd  音频门控单元测试
sim/tb_chain.vhd         端到端帧协议测试（3 个 demo 帧）


备注
----
- simulation/modelsim/ 里是修复前的旧网表，本包已排除；
  请使用 simulation/questa/QuadrupleBuffer.vho。
- sim/work/、sim/work_top/ 是编译产物，本包已排除，首次运行会自动生成。
- 本包是快照，不包含 .git 历史。
