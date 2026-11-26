library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity PulseExpander is
	 generic(OUTPUT_LENGTH_CYCLES: integer := 8);
    port (
        clk_in : in  STD_LOGIC;
		  pulse_in : in STD_LOGIC;
        pulse_out: out STD_LOGIC
	 );
end PulseExpander;

architecture Behavioral of PulseExpander is
    signal sCounter : integer range 0 to OUTPUT_LENGTH_CYCLES := 0;
	 signal s_pulse_out: STD_LOGIC := '0';
begin
    pPulseExpander: process (clk_in) begin
        if rising_edge(clk_in) then
            -- A new pulse (re)loads the counter, otherwise it counts down.
            -- Now only one assignment ever reaches sCounter, so a reload
            -- is no longer overwritten by the decrement.
            if (pulse_in = '1') then
                sCounter <= OUTPUT_LENGTH_CYCLES;
            elsif (sCounter /= 0) then
                sCounter <= sCounter - 1;
            end if;

            -- Output is high while the counter is running. It uses the
            -- pre-edge counter value, so it rises one clock after the
            -- triggering pulse -- same timing as the original code.
            if (sCounter /= 0) then
                s_pulse_out <= '1';
            else
                s_pulse_out <= '0';
            end if;
        end if;
    end process;

    pulse_out <= s_pulse_out;
end Behavioral;
