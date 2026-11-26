library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

-- Minimal reproduction of the PulseExpander glitch, using the old project's
-- own PulseExpander/LatchBuffer/PhaseLine sources.
--
-- It wires the same three stages as the top level:
--
--   swap_in (held high, like Distribute.swap_out after 0xFD)
--        -> PulseExpander (OUTPUT_LENGTH_CYCLES = 16)
--        -> LatchBuffer (clocked by COUNT(2))
--        -> PhaseLine.swap
--
-- PhaseLine is loaded with phase 13 through one set pulse, then the input is
-- held high for 200 us and every rising edge on the latch output / change of
-- the active phase is reported.
--
-- Pre-fix expander: one low glitch per 17 CLK_8 -> latch sees a low once per
-- 136 CLK_8 (26.56 us at 5.12 MHz) -> PhaseLine swaps back and forth about
-- once per drive cycle.
-- Fixed expander: a single clean swap.
entity tb_expander_hold is
end entity;

architecture sim of tb_expander_hold is

    constant CLK8_PERIOD : time := 195313 ps;      -- 5.12 MHz
    constant HOLD_TIME   : time := 200 us;         -- ~7.5 glitch beats

    signal clk8      : std_logic := '0';
    signal count     : std_logic_vector(7 downto 0) := (others => '0');
    signal clk       : std_logic;
    signal swap_in   : std_logic := '0';
    signal set_in    : std_logic := '0';
    signal swap_exp  : std_logic;
    signal swap_e    : std_logic;
    signal phase     : std_logic_vector(5 downto 0) := (others => '0');
    signal finished  : boolean := false;

    -- Probe PhaseLine internals (VHDL-2008 external names).
    signal s_cur     : integer;
    signal s_prev    : integer;

    signal edges     : integer := 0;
    signal changes   : integer := 0;

begin

    clk8 <= not clk8 after CLK8_PERIOD / 2 when not finished else '0';
    clk  <= count(2);

    s_cur  <= << signal .tb_expander_hold.dut.s_phaseCurrent : integer range 0 to 63 >>;
    s_prev <= << signal .tb_expander_hold.dut.s_phasePrev    : integer range 0 to 63 >>;

    counter : process (clk8)
    begin
        if rising_edge(clk8) then
            count <= std_logic_vector(unsigned(count) + 1);
        end if;
    end process;

    exp : entity work.PulseExpander
        generic map (OUTPUT_LENGTH_CYCLES => 16)
        port map (clk_in => clk8, pulse_in => swap_in, pulse_out => swap_exp);

    lat : entity work.LatchBuffer
        port map (clk_in => clk, signal_in => swap_exp, signal_out => swap_e);

    dut : entity work.PhaseLine
        port map (
            clk     => clk,
            set     => set_in,
            swap    => swap_e,
            phase   => phase,
            counter => count(7 downto 3),
            pulse   => open
        );

    monitor : process
        variable prev_swap : std_logic := '0';
        variable prev_cur  : integer  := 0;
        variable n_edges   : integer  := 0;
        variable n_changes : integer  := 0;
    begin
        loop
            wait until rising_edge(clk);
            if swap_e = '1' and prev_swap = '0' then
                n_edges := n_edges + 1;
                report "swap_e rise #" & integer'image(n_edges) &
                       " at " & time'image(now) &
                       "  (current=" & integer'image(s_cur) &
                       ", prev=" & integer'image(s_prev) & ")"
                    severity note;
            end if;
            prev_swap := swap_e;

            if s_cur /= prev_cur then
                n_changes := n_changes + 1;
                report "s_phaseCurrent changed " & integer'image(prev_cur) &
                       " -> " & integer'image(s_cur) &
                       " at " & time'image(now)
                    severity note;
                prev_cur := s_cur;
            end if;

            edges   <= n_edges;
            changes <= n_changes;
        end loop;
    end process;

    stimulus : process
    begin
        wait for 2 us;

        -- Load phase 13 into the staging buffer (one set pulse).
        phase  <= std_logic_vector(to_unsigned(13, 6));
        set_in <= '1';
        wait until rising_edge(clk);
        set_in <= '0';
        wait until rising_edge(clk);

        report "holding swap_in high for " & time'image(HOLD_TIME) severity note;
        swap_in <= '1';                 -- like Distribute.swap_out after 0xFD
        wait for HOLD_TIME;
        swap_in <= '0';
        wait for 20 us;

        report "RESULT swap_e_rising_edges=" & integer'image(edges) &
               " s_phaseCurrent_changes=" & integer'image(changes) &
               " final_current=" & integer'image(s_cur) &
               " final_prev=" & integer'image(s_prev)
            severity note;

        finished <= true;
        wait;
    end process;

end architecture;
