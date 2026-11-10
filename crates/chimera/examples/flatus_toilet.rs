//! The flatulence creature's toilet bowl, predicted: `cargo run --release -p chimera --example
//! flatus_toilet [seat=<cm²> …]` prints the bowl's air volume, the lumped Helmholtz estimate from
//! the geometry (`flatus::toilet_helmholtz`), and the peaks of the linearised network's transfer
//! function from a flow injected at the cleft's mouth end (the cheeks' valve cut, as an ideal flow
//! source) to the radiated flow, with the toilet on and off, from 40 Hz to 2 kHz. The bowl's leak
//! ports all open into one outlet, a loop the engine's tree solver (`transfer_function`) would
//! drop, so the network is solved here by full nodal analysis (the same lumped elements).
//!
//! `flatus_toilet render <dir> [param=value …]` instead renders the held voice (3 s at the
//! defaults) and every call, each from a fresh voice, with the toilet off and on, as raw
//! little-endian f32 at 48 kHz (`<dir>/<part>-off.f32`, `-on.f32`), 20 dB down (the voice's
//! level 0.1) so the output limiter's knee is never reached, and measures each as `chimera
//! render creature` does (its span within 30 dB of the loudest 10 ms; level with the 20 dB added
//! back; YIN f0 over 40 ms frames, periodic when aperiodicity < 0.3; spectral centroid). It also
//! tracks the distal ring's gap sample by sample and gives its own f0 and periodic fraction over
//! the same span (the sphincter's oscillation, apart from what the bowl does to the sound).
use chimera::airway::frequency::{find_peaks, linspace};
use chimera::airway::network::LinearElements;
use chimera::physics::{C_SOUND, RHO};

#[derive(Clone, Copy)]
struct C(f64, f64);
impl C {
    fn add(self, o: C) -> C {
        C(self.0 + o.0, self.1 + o.1)
    }
    fn sub(self, o: C) -> C {
        C(self.0 - o.0, self.1 - o.1)
    }
    fn mul(self, o: C) -> C {
        C(self.0 * o.0 - self.1 * o.1, self.0 * o.1 + self.1 * o.0)
    }
    fn inv(self) -> C {
        let d = self.0 * self.0 + self.1 * self.1;
        C(self.0 / d, -self.1 / d)
    }
    fn abs(self) -> f64 {
        self.0.hypot(self.1)
    }
}

/// |U_rad/U_in| and the radiated pressure (dB, ∝ ω·|U_rad|) for a flow injected at `inject`,
/// branches in `cut` removed: the nodal equations Y·p = I solved per frequency (Gaussian
/// elimination), with the same shunts (compliance, walls, scaled radiation loads) and branch
/// impedances (R + jωL) as `frequency::transfer_function`.
fn nodal_tf(el: &LinearElements, inject: usize, freqs: &[f64], cut: &[usize]) -> (Vec<f64>, Vec<f64>) {
    let n = el.n_nodes;
    let mut rad = vec![None; n];
    for (r, &k) in el.rad_nodes.iter().enumerate() {
        rad[k] = Some(r);
    }
    let (mut mag, mut db) = (Vec::new(), Vec::new());
    for &f in freqs {
        let w = 2.0 * std::f64::consts::PI * f;
        let mut y = vec![vec![C(0.0, 0.0); n]; n];
        let mut ry = vec![C(0.0, 0.0); n];
        for k in 0..n {
            let mut g = C(0.0, w * el.c[k]);
            if el.wall_area[k] > 0.0 {
                g = g.add(C(el.wall_r[k], w * el.wall_m[k] - el.wall_k[k] / w).inv().mul(C(el.wall_area[k], 0.0)));
            }
            if let Some(r) = rad[k] {
                let a = el.rad_area[r];
                let lr = (8.0 * RHO) / (3.0 * std::f64::consts::PI * (std::f64::consts::PI * a).sqrt());
                let rr = (128.0 * RHO * C_SOUND) / (9.0 * std::f64::consts::PI * std::f64::consts::PI * a);
                ry[k] = C(1.0 / rr * el.rad_scale[r], -1.0 / (w * lr) * el.rad_scale[r]);
                g = g.add(ry[k]);
            }
            if el.fixed[k] {
                g = g.add(C(1e30, 0.0));
            }
            y[k][k] = y[k][k].add(g);
        }
        for j in 0..el.n_branches {
            if !el.open[j] || cut.contains(&j) {
                continue;
            }
            let yb = C(el.r[j], w * el.l[j]).inv();
            let (a, b) = (el.a[j], el.b[j]);
            y[a][a] = y[a][a].add(yb);
            y[b][b] = y[b][b].add(yb);
            y[a][b] = y[a][b].sub(yb);
            y[b][a] = y[b][a].sub(yb);
        }
        let mut rhs = vec![C(0.0, 0.0); n];
        rhs[inject] = C(1.0, 0.0);
        for col in 0..n {
            let piv = (col..n).max_by(|&i, &j| y[i][col].abs().partial_cmp(&y[j][col].abs()).unwrap()).unwrap();
            y.swap(col, piv);
            rhs.swap(col, piv);
            let inv = y[col][col].inv();
            for row in col + 1..n {
                let m = y[row][col].mul(inv);
                if m.abs() == 0.0 {
                    continue;
                }
                for k in col..n {
                    y[row][k] = y[row][k].sub(m.mul(y[col][k]));
                }
                rhs[row] = rhs[row].sub(m.mul(rhs[col]));
            }
        }
        let mut p = vec![C(0.0, 0.0); n];
        for row in (0..n).rev() {
            let mut acc = rhs[row];
            for k in row + 1..n {
                acc = acc.sub(y[row][k].mul(p[k]));
            }
            p[row] = acc.mul(y[row][row].inv());
        }
        let mut u = C(0.0, 0.0);
        for k in 0..n {
            if rad[k].is_some() {
                u = u.add(p[k].mul(ry[k]));
            }
        }
        mag.push(u.abs());
        db.push(20.0 * (u.abs() * w + 1e-30).log10());
    }
    (mag, db)
}
use chimera::creatures::flatus::{bowl_volume, toilet_helmholtz};
use chimera::analysis::fft::{Fft, hann};
use chimera::analysis::pitch::{YinOpts, yin_pitch};
use chimera::creatures::{CreatureVoice, creature_by_id};

/// `chimera render creature`'s measurement (crates/chimera-cli/src/render.rs `measure`), with
/// the level 20 dB up (the render's level 0.1).
fn span_of(x: &[f32], fs: f64) -> (usize, usize) {
    let win = (0.01 * fs).round() as usize;
    let rms: Vec<f64> = x.chunks(win).map(|c| (c.iter().map(|v| (*v as f64).powi(2)).sum::<f64>() / c.len() as f64).sqrt()).collect();
    let top = rms.iter().cloned().fold(0.0, f64::max);
    let on: Vec<usize> = (0..rms.len()).filter(|&i| rms[i] > top * 10f64.powf(-30.0 / 20.0)).collect();
    (on[0] * win, ((on[on.len() - 1] + 1) * win).min(x.len()))
}

/// The ring's gap over the sound's span: YIN f0 median and periodic fraction over 40 ms frames
/// in which it is open.
fn gap_f0(gap: &[f32], x: &[f32], fs: f64) -> String {
    let (a, b) = span_of(x, fs);
    let n = (0.04 * fs).round() as usize;
    let win = (0.01 * fs).round() as usize;
    let (mut f0s, mut frames, mut i) = (Vec::new(), 0, a);
    while i + n <= b {
        let fr: Vec<f64> = gap[i..i + n].iter().map(|&v| v as f64).collect();
        if fr.iter().any(|&g| g > 0.0) {
            frames += 1;
            let mean = fr.iter().sum::<f64>() / n as f64;
            let fr: Vec<f64> = fr.iter().map(|g| g - mean).collect();
            let p = yin_pitch(&fr, fs, YinOpts { min_f0: Some(30.0), max_f0: Some(2000.0), ..Default::default() });
            if p.f0 > 0.0 && p.aperiodicity < 0.3 {
                f0s.push(p.f0);
            }
        }
        i += win;
    }
    f0s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    if f0s.is_empty() {
        return format!("ring: no periodic frames of {frames} open");
    }
    format!("ring: f0 {:.0} Hz ({:.0}% periodic)", f0s[f0s.len() / 2], 100.0 * f0s.len() as f64 / frames.max(1) as f64)
}

fn measure(x: &[f32], fs: f64) -> String {
    let win = (0.01 * fs).round() as usize;
    let rms: Vec<f64> = x.chunks(win).map(|c| (c.iter().map(|v| (*v as f64).powi(2)).sum::<f64>() / c.len() as f64).sqrt()).collect();
    let top = rms.iter().cloned().fold(0.0, f64::max);
    if top < 1e-7 {
        return "silent".to_string();
    }
    let (a, b) = span_of(x, fs);
    let span = &x[a..b];
    let level = (span.iter().map(|v| (*v as f64).powi(2)).sum::<f64>() / span.len() as f64).sqrt();
    let n = (0.04 * fs).round() as usize;
    let (mut f0s, mut frames, mut i) = (Vec::new(), 0, 0);
    while i + n <= span.len() {
        let fr: Vec<f64> = span[i..i + n].iter().map(|&v| v as f64).collect();
        let e = (fr.iter().map(|v| v * v).sum::<f64>() / n as f64).sqrt();
        if e > top * 0.1 {
            frames += 1;
            let p = yin_pitch(&fr, fs, YinOpts { min_f0: Some(30.0), max_f0: Some(2000.0), ..Default::default() });
            if p.f0 > 0.0 && p.aperiodicity < 0.3 {
                f0s.push(p.f0);
            }
        }
        i += win;
    }
    f0s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let q = |p: f64| f0s[((f0s.len() - 1) as f64 * p).round() as usize];
    let f0 = if f0s.is_empty() { "f0 none".to_string() } else { format!("f0 {:.0} Hz ({:.0}–{:.0}, {:.0}% periodic)", q(0.5), q(0.05), q(0.95), 100.0 * f0s.len() as f64 / frames.max(1) as f64) };
    let m = 4096;
    let fft = Fft::new(m);
    let w = hann(m);
    let mut pw = vec![0.0f64; m / 2];
    let mut j = 0;
    while j + m <= span.len() {
        let mut re: Vec<f64> = (0..m).map(|k| span[j + k] as f64 * w[k]).collect();
        let mut im = vec![0.0; m];
        fft.transform(&mut re, &mut im);
        for k in 0..m / 2 {
            pw[k] += re[k] * re[k] + im[k] * im[k];
        }
        j += m / 2;
    }
    let tot: f64 = pw.iter().sum();
    let cen = if tot > 0.0 { pw.iter().enumerate().map(|(k, p)| k as f64 * fs / m as f64 * p).sum::<f64>() / tot } else { 0.0 };
    format!("{:.2} s, {:.1} dBFS rms, {f0}, centroid {cen:.0} Hz", (b - a) as f64 / fs, 20.0 * level.log10() + 20.0)
}

fn render(dir: &str, extra: &[(usize, f64)]) {
    let def = creature_by_id("flatulence").unwrap();
    std::fs::create_dir_all(dir).unwrap();
    let parts: Vec<Option<usize>> = std::iter::once(None).chain((0..def.calls.len()).map(Some)).collect();
    for part in parts {
        for on in [0.0, 1.0] {
            let mut init = extra.to_vec();
            init.push((def.param_index("toilet").unwrap(), on));
            let mut v = CreatureVoice::new(def, 48000.0, &init);
            v.level = 0.1;
            let (name, secs) = match part {
                None => {
                    v.set_gate(1.0);
                    ("hold", 3.0)
                }
                Some(c) => {
                    let call = &def.calls[c];
                    v.play_call_id(call.id, None, 1.0);
                    (call.id, call.keys[call.keys.len() - 1].t + 0.5)
                }
            };
            // sample by sample (the output doesn't depend on the block size), the ring's gap too
            let total = (secs * 48000.0) as usize + if part.is_none() { 24000 } else { 0 };
            let mut out = vec![0.0f32; total];
            let mut gap = vec![0.0f32; total];
            let mut src = Vec::new();
            for i in 0..total {
                if part.is_none() && i == (secs * 48000.0) as usize {
                    v.set_gate(0.0);
                }
                v.render(&mut out[i..i + 1]);
                v.sim.source_state(&mut src);
                gap[i] = src.iter().find(|(k, _)| *k == "gap").unwrap().1 as f32;
            }
            let bytes: Vec<u8> = out.iter().flat_map(|x| x.to_le_bytes()).collect();
            let path = format!("{dir}/{name}-{}.f32", if on > 0.5 { "on" } else { "off" });
            std::fs::write(&path, bytes).unwrap();
            println!("{name:>9} {}: {}; {}", if on > 0.5 { "on " } else { "off" }, measure(&out, 48000.0), gap_f0(&gap, &out, 48000.0));
        }
    }
}

fn main() {
    let def = creature_by_id("flatulence").unwrap();
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.first().map(String::as_str) == Some("render") {
        let extra: Vec<(usize, f64)> = args[2..].iter().map(|a| a.split_once('=').expect("param=value")).map(|(k, v)| (def.param_index(k).expect("param"), v.parse().unwrap())).collect();
        render(&args[1], &extra);
        return;
    }
    let leaks: Vec<f64> = {
        let a: Vec<f64> = std::env::args().skip(1).filter_map(|a| a.strip_prefix("seat=").map(|v| v.parse().unwrap())).collect();
        if a.is_empty() { vec![5.0, 20.0, 51.0, 100.0, 200.0] } else { a }
    };
    println!("bowl air: {:.0} cm³", bowl_volume());
    let fr = linspace(40.0, 2000.0, 1961);
    for leak in leaks {
        let mut db = Vec::new();
        for on in [0.0, 1.0] {
            let v = CreatureVoice::new(def, 48000.0, &[(def.param_index("toilet").unwrap(), on), (def.param_index("seat").unwrap(), leak)]);
            let net = v.sim.net().unwrap();
            let cleft = v.sim.tubes().iter().find(|(n, _)| *n == "cleft").unwrap().1;
            let el = net.linear_elements();
            // the cheeks' port feeds the cleft's first node: cut it (an ideal flow source)
            let cut: Vec<usize> = (0..el.n_branches).filter(|&j| el.b[j] == cleft.first_node() && el.a[j] != cleft.first_node() + 1).collect();
            let (mag, pdb) = nodal_tf(&el, cleft.first_node(), &fr, &cut);
            if on > 0.5 {
                let peaks = find_peaks(&fr, &mag, 40.0);
                let shown: Vec<String> = peaks.iter().map(|p| format!("{:.0} Hz ({:+.1} dB, bw {:.0})", p.freq, p.db, p.bw)).collect();
                println!("leak {leak:5.0} cm²: Helmholtz estimate {:.0} Hz; the network's peaks (toilet on) {}", toilet_helmholtz(leak), if shown.is_empty() { "none".to_string() } else { shown.join(", ") });
            }
            db.push(pdb);
        }
        let at = |f: f64| {
            let i = fr.iter().position(|&x| x >= f).unwrap();
            db[1][i] - db[0][i]
        };
        println!("    radiated pressure, on re off, at 63/100/200/500/1000/2000 Hz: {:+.1} {:+.1} {:+.1} {:+.1} {:+.1} {:+.1} dB", at(63.0), at(100.0), at(200.0), at(500.0), at(1000.0), at(1999.0));
    }
}
