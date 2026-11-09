//! Ventricular (false) vocal folds as a valve phase-locked to the true folds: kargyraa.
//!
//! In kargyraa the ventricular folds, about a centimetre above the glottis, vibrate at half the
//! vocal folds' rate and close once every two glottal cycles (Bailly, Henrich & Pelorson 2010).
//! Every other glottal pulse meets a nearly shut valve and is choked, so the radiated sound
//! repeats every two cycles: its pitch is an octave below the folds', and the timbre is rough
//! (the jet through the narrow valve is turbulent).
//!
//! Like the parametric glottis, this is an area waveform, not a self-oscillating mass: the
//! valve's area follows the glottal cycle, so the subharmonic is exact. The airway does the rest
//! (the valve caps the minimum area of the tract node at the ventricular folds, which sets the
//! jet's Borda–Carnot loss and its turbulence).

use crate::math::{PI, cos, exp};

#[derive(Clone, Debug)]
pub struct VentricularFolds {
    /// target depth 0..1: how far the valve closes on its closing cycle
    pub depth: f64,
    /// 0..1: how much each closure's depth varies at random (0: kargyraa's exact period doubling;
    /// toward 1: the irregular, partial supraglottal vibration of a rock singer's "dist" tone,
    /// Borch, Sundberg, Lindestad & Thalén 2004)
    pub irregularity: f64,
    /// 0..1: how often a cycle's closure alternates with the last one's (period doubling: growl)
    /// rather than being drawn at random
    pub sub: f64,
    closed: bool,
    depth_sm: f64,
    sm_coef: f64,
    /// this closure's share of the depth (1 when regular)
    this_closure: f64,
    last_phi: f64,
    rng: u32,
}

/// Centre of the closure within the two-cycle period (0..1): the second cycle's open phase
/// (glottal pulses rise over the first ~30 % of a cycle), so that cycle's pulse is the one choked.
const CLOSE_AT: f64 = 0.65;
/// Half-width of the closure (fraction of the two-cycle period).
const HALF_WIDTH: f64 = 0.25;
/// Rasp: a closure's centre in the glottal cycle (the pulse) and its half-width (of a cycle).
const RASP_AT: f64 = 0.3;
const RASP_HALF: f64 = 0.35;
/// The narrowest the valve gets, as a fraction of its open area: it chokes the jet but never
/// seals (a seal stops the flow within a sample, a click).
const FLOOR: f64 = 0.01;

impl VentricularFolds {
    pub fn new(fs: f64) -> Self {
        VentricularFolds { depth: 0.0, irregularity: 0.0, sub: 0.0, closed: false, depth_sm: 0.0, sm_coef: 1.0 - exp(-1.0 / (0.02 * fs)), this_closure: 1.0, last_phi: 0.0, rng: 0x9E37_79B9 }
    }

    /// Whether the valve is (still) acting: false once it has relaxed fully open.
    #[inline]
    pub fn active(&self) -> bool {
        self.depth > 0.0 || self.depth_sm > 1e-5
    }

    /// Rasp: each glottal cycle the folds may close (with chance `irregularity`) during its pulse,
    /// to an open fraction drawn log-uniformly between 1 and 10^(-2·depth): partial, aperiodic
    /// supraglottal closures that roughen the voice without halving its pitch.
    fn next_rasp(&mut self, glottal_phase: f64) -> f64 {
        if glottal_phase < self.last_phi {
            let (u, v, w) = (self.draw(), self.draw(), self.draw());
            self.closed = if w < self.sub { !self.closed } else { u < self.irregularity };
            self.this_closure = if self.closed { crate::math::pow(10.0, -2.0 * self.depth_sm * v) } else { 1.0 };
        }
        self.last_phi = glottal_phase;
        let d = (glottal_phase - RASP_AT).abs();
        let g = if d < RASP_HALF { 0.5 + 0.5 * cos(PI * d / RASP_HALF) } else { 0.0 };
        let s = 1.0 - (1.0 - self.this_closure) * g;
        if s < FLOOR { FLOOR } else { s }
    }

    /// xorshift32 in 0..1 (deterministic)
    fn draw(&mut self) -> f64 {
        self.rng ^= self.rng << 13;
        self.rng ^= self.rng >> 17;
        self.rng ^= self.rng << 5;
        self.rng as f64 / u32::MAX as f64
    }

    /// Area scale (FLOOR..1) for this sample, from the glottal cycle phase (0..1) and whether
    /// this is an odd glottal cycle.
    #[inline]
    pub fn next(&mut self, glottal_phase: f64, odd_cycle: bool) -> f64 {
        self.depth_sm += self.sm_coef * (self.depth - self.depth_sm);
        if self.irregularity > 0.0 {
            return self.next_rasp(glottal_phase);
        }
        let phi = 0.5 * (glottal_phase + if odd_cycle { 1.0 } else { 0.0 });
        let d = (phi - CLOSE_AT).abs();
        let g = if d < HALF_WIDTH { 0.5 + 0.5 * cos(PI * d / HALF_WIDTH) } else { 0.0 };
        let s = 1.0 - self.depth_sm * g;
        if s < FLOOR { FLOOR } else { s }
    }
}
