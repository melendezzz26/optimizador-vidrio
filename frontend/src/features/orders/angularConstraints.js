// Lengths are normalized by the longest edge. Headings encode exact edge lengths;
// only closure and selected interior angles are solved. No drawing angle is fixed.
function solveLinear(matrix, rhs) {
  const a = matrix.map((row, i) => [...row, rhs[i]]);
  const n = rhs.length;
  for (let k = 0; k < n; k++) {
    let pivot = k;
    for (let i = k + 1; i < n; i++) if (Math.abs(a[i][k]) > Math.abs(a[pivot][k])) pivot = i;
    [a[k], a[pivot]] = [a[pivot], a[k]];
    if (Math.abs(a[k][k]) < 1e-18) return null;
    const divisor = a[k][k];
    for (let j = k; j <= n; j++) a[k][j] /= divisor;
    for (let i = 0; i < n; i++) if (i !== k) {
      const factor = a[i][k];
      for (let j = k; j <= n; j++) a[i][j] -= factor * a[k][j];
    }
  }
  return a.map(row => row[n]);
}

export function headingsFromVertices(points) {
  const angles = points.map((p, i) => Math.atan2(points[(i + 1) % points.length][1] - p[1], points[(i + 1) % points.length][0] - p[0]));
  return angles.slice(1).map(angle => (angle - angles[0] + 2 * Math.PI) % (2 * Math.PI));
}

export function solveAngularConstraints(sides, fixed, initial) {
  const n = sides.length;
  function evaluate(headings) {
    const all = [0, ...headings];
    const residual = [0, 0];
    const jacobian = [headings.map((h, j) => -sides[j + 1] * Math.sin(h)),
      headings.map((h, j) => sides[j + 1] * Math.cos(h))];
    all.forEach((h, i) => { residual[0] += sides[i] * Math.cos(h); residual[1] += sides[i] * Math.sin(h); });
    for (const { vertex, angle } of fixed) {
      const row = Array(n - 1).fill(0);
      if (vertex === 0) {
        residual.push(all[n - 1] - Math.PI - Number(angle) * Math.PI / 180);
        row[n - 2] = 1;
      } else {
        residual.push(all[vertex] - all[vertex - 1] - Math.PI + Number(angle) * Math.PI / 180);
        row[vertex - 1] = 1;
        if (vertex > 1) row[vertex - 2] = -1;
      }
      jacobian.push(row);
    }
    return { residual, jacobian, cost: residual.reduce((sum, r) => sum + r * r, 0) };
  }
  let headings = [...initial];
  let damping = 1e-3;
  let state = evaluate(headings);
  for (let iteration = 0; iteration < 180 && state.cost > 1e-24; iteration++) {
    const { residual, jacobian } = state;
    // Minimum displacement step also works when fewer than n-3 angles are fixed.
    const normal = headings.map((_, i) => headings.map((_, j) =>
      jacobian.reduce((sum, row) => sum + row[i] * row[j], 0) + (i === j ? damping : 0)));
    const rhs = headings.map((_, i) => -jacobian.reduce((sum, row, k) => sum + row[i] * residual[k], 0));
    const step = solveLinear(normal, rhs);
    if (!step) return null;
    const next = headings.map((h, i) => h + step[i]);
    const candidate = evaluate(next);
    if (candidate.cost < state.cost) {
      headings = next; state = candidate; damping = Math.max(1e-12, damping / 3);
    } else damping = Math.min(1e12, damping * 10);
    if (damping === 1e12) break;
  }
  if (state.cost > 1e-18) return null;
  const points = [[0, 0]];
  [0, ...headings].slice(0, -1).forEach((h, i) => points.push([
    points[i][0] + sides[i] * Math.cos(h), points[i][1] + sides[i] * Math.sin(h),
  ]));
  return points; // Caller must independently validate all constraints and convexity.
}
