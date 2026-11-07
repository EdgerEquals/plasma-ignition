**Plasma Ignition Project Update**  
**7 November 2026**

Dear Dr Vikas,

Thank you again for your careful feedback on the earlier two-stage concept. This note brings you up to date with where the work has gone.

### Where we started
In August I shared a two-stage architecture that used a 60 kV trigatron for the ionization pulse and a second high-current stage for energy delivery, targeting roughly 1 J per pulse with multiple pulses per power stroke. Your questions about rise time versus flashover, insulation stress, spark-plug lifetime, and the practical limits of trigatron recovery were exactly the right ones.

### What we learned
The trigatron approach worked on paper but brought high cost, heater-power (or cold-cathode) complexity, and recovery-time constraints at the burst rates we wanted. After further work we moved to a simpler first-principles design that keeps the useful ideas (fast high-voltage kernel, separate energy delivery, external timing) while removing the expensive switches.

### Where we are now
We have locked a first-prototype design for a stock Honda GX120 running diluted HHO + water mist:

- Stock BP6ES plug remains in the head.  
- Outer copper sleeve provides the coaxial ground return against the head.  
- Bottom adapter + 3" × 100 mm tri-clamp stainless spool forms the enclosure.  
- Inside the spool: saturable reactor, copper discs, four doorknob capacitors, and an annular charger board (12 V flyback + 3-stage Cockcroft-Walton).  
- Single nylon bolt clamps the stack.  
- External MCU sends only a charge-enable signal.  
- No head machining required for the first unit.

The full technical handover is in the repository:  
[docs/TECHNICAL_HANDOVER.md](https://github.com/EdgerEquals/plasma-ignition/blob/main/docs/TECHNICAL_HANDOVER.md)

### Next steps
1. Complete the annular charger-board schematic and layout (Claude is helping with the PCB files).  
2. Order the board from PCBWay and fabricate the mechanical parts.  
3. Build and bench-test the first prototype.  
4. Collect measured voltage, current, and discharge-energy data for the next discussion.

I would value your thoughts on the new topology whenever you have time. The measured data from the first unit will be the most useful next input.

Kind regards,  
Danny
