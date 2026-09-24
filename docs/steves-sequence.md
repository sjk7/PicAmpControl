# Steve's TX Sequence (band switching at key-down)

The operator's instruction, recorded verbatim for future refinement (2026-09-24).

> All the band switching must be done immediately on key down. Only once we have sniffed
> enough of the frequency and confirmed band relay is switching or switched and
> correct, then you can continue with the rest of the ptt sequence. Just inject the
> band switching between when rx goes low and the tx/tx relays are switched. It's
> simple. The band relays have the whole of the rest of the sequence to engage, which
> is plenty of time. Only refuse to tx if you cannot detect the frequency at key down.

## What this means, concretely

1. The moment PTT/RX goes low (key-down), **sniff the frequency** and switch the band
   relays to the measured band. This happens **before** the T/R (OUTPUT_TX) relay is
   switched, so the T/R relay never closes onto a moving or wrong filter.
2. **Wait for confirmation** — the frequency counter has stabilised a band, and the band
   relay is switching / has switched to the correct position — **before** proceeding
   with the rest of the PTT sequence (T/R relay, then TX_VCC, then TX_BIAS).
3. The band relays have the **entire rest of the sequence** (the inter-stage
   `tx_vcc_delay_ms` / `tx_bias_delay_ms` windows, default 20 ms each) to finish
   engaging — far more than their operate time. There is no need for any separate
   "remembered band", "instant warm re-key", "verify", or "fold-back" machinery.
4. **The only reason to refuse to transmit** is that the frequency **cannot be detected
   at key-down**. If the band can be measured, transmit on it; if not, stay in bypass.

## Open questions to settle when refining

- How long is "enough sniffing" at key-down before we decide the frequency is present
  (and how long before we refuse)?
- What happens to the old "remembered band" cache (`g_band_cache_valid`,
  `g_band_cache_band`, idle-timeout expiry)? Candidate: keep the cache purely as a
  *fallback* only when key-down sniffing finds no frequency, or drop it entirely.
- The simulator does not model Timer1's external clock (T1CKI), so "sniff the frequency
  at key-down" is exercised by injecting TMR1H/TMR1L; the pin/PPS/prescaler path is
  bench-only.
