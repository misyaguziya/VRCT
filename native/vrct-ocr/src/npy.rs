//! The numpy 1.26 behaviours RapidOCR's results depend on.
//!
//! Ported from numpy 1.26.4 (https://github.com/numpy/numpy): core/src/npysort/quicksort.cpp
//! (aquicksort_; on Windows numpy does not dispatch to x86-simd-sort), core/src/umath/
//! loops_utils.h.src (pairwise summation) and core/src/multiarray/calculation.c (round).
//! Copyright (c) 2005-2023, NumPy Developers. BSD-3-Clause license.

/// np.argsort(values) with the default kind (introsort). Ties keep numpy's order, which the
/// batching of RapidOCR's classifier / recognizer depends on.
pub fn argsort(v: &[f64]) -> Vec<usize> {
    let num = v.len();
    let mut tosort: Vec<usize> = (0..num).collect();
    if num < 2 {
        return tosort;
    }
    // numpy's LT: NaN sorts last
    let less = |a: f64, b: f64| a < b || (b.is_nan() && !a.is_nan());
    // ponytail: the depth limit's heapsort fallback is not ported (needs > 2*log2(n) bad splits;
    // never reached with a few dozen text lines)
    let mut stack: Vec<(usize, usize)> = Vec::new();
    let (mut pl, mut pr) = (0usize, num - 1);
    loop {
        while pr - pl > 15 {
            let pm = pl + ((pr - pl) >> 1);
            if less(v[tosort[pm]], v[tosort[pl]]) {
                tosort.swap(pm, pl);
            }
            if less(v[tosort[pr]], v[tosort[pm]]) {
                tosort.swap(pr, pm);
            }
            if less(v[tosort[pm]], v[tosort[pl]]) {
                tosort.swap(pm, pl);
            }
            let vp = v[tosort[pm]];
            let mut pi = pl;
            let mut pj = pr - 1;
            tosort.swap(pm, pj);
            loop {
                loop {
                    pi += 1;
                    if !less(v[tosort[pi]], vp) {
                        break;
                    }
                }
                loop {
                    pj -= 1;
                    if !less(vp, v[tosort[pj]]) {
                        break;
                    }
                }
                if pi >= pj {
                    break;
                }
                tosort.swap(pi, pj);
            }
            let pk = pr - 1;
            tosort.swap(pi, pk);
            // push the larger partition, continue with the smaller
            if pi - pl < pr - pi {
                stack.push((pi + 1, pr));
                pr = pi - 1;
            } else {
                stack.push((pl, pi - 1));
                pl = pi + 1;
            }
        }
        // insertion sort
        for pi in pl + 1..=pr {
            let vi = tosort[pi];
            let vp = v[vi];
            let mut pj = pi;
            while pj > pl && less(vp, v[tosort[pj - 1]]) {
                tosort[pj] = tosort[pj - 1];
                pj -= 1;
            }
            tosort[pj] = vi;
        }
        match stack.pop() {
            Some((l, r)) => (pl, pr) = (l, r),
            None => break,
        }
    }
    tosort
}

/// DOUBLE_pairwise_sum.
fn pairwise_sum(a: &[f64]) -> f64 {
    let n = a.len();
    if n < 8 {
        let mut res = -0.0;
        for &x in a {
            res += x;
        }
        res
    } else if n <= 128 {
        let mut r = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7]];
        let mut i = 8;
        while i < n - (n % 8) {
            for k in 0..8 {
                r[k] += a[i + k];
            }
            i += 8;
        }
        let mut res = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]));
        while i < n {
            res += a[i];
            i += 1;
        }
        res
    } else {
        let mut n2 = n / 2;
        n2 -= n2 % 8;
        pairwise_sum(&a[..n2]) + pairwise_sum(&a[n2..])
    }
}

/// np.mean(list_of_floats): the pairwise sum of all elements (checked against numpy 1.26.4 for
/// 3..300 elements), then true_divide by the count.
pub fn mean(a: &[f64]) -> f64 {
    pairwise_sum(a) / a.len() as f64
}

/// ndarray.round(decimals) for float64 with decimals > 0: multiply, rint, divide.
pub fn round(x: f64, decimals: i32) -> f64 {
    let f = 10f64.powi(decimals);
    (x * f).round_ties_even() / f
}

/// Python's round(x, ndigits): correctly rounded (half to even on the exact binary value).
pub fn py_round(x: f64, ndigits: usize) -> f64 {
    format!("{x:.ndigits$}").parse().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn argsort_matches_numpy_insertion_and_partition() {
        // checked against numpy 1.26.4: np.argsort(v)
        let v = [3.0, 1.0, 2.0, 1.0, 5.0, 0.5, 2.0, 2.0, 9.0, 1.0, 7.0, 3.0, 3.0, 0.0, 4.0, 2.0, 6.0, 1.0, 8.0, 2.0];
        assert_eq!(argsort(&v), [13, 5, 9, 1, 17, 3, 15, 19, 6, 2, 7, 11, 12, 0, 14, 4, 16, 10, 18, 8]);
    }

    #[test]
    fn python_round_ties_to_even() {
        assert_eq!(py_round(0.015625, 5), 0.01562);
        assert_eq!(round(0.015625, 5), 0.01562);
    }

    #[test]
    fn round_not_a_tie() {
        // np.float64(0.9995149999999998).round(5): x * 1e5 = 99951.49999999999 -> 0.99951
        assert_eq!(round(0.9995149999999998, 5), 0.99951);
    }

    #[test]
    fn mean_like_numpy() {
        let v: Vec<f64> = (0..20).map(|i| 0.1 * i as f64 + 0.01).collect();
        assert_eq!(mean(&v), 0.96); // np.mean(v)
    }
}
