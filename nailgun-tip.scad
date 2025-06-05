$fa = 1;
$fs = 0.4;
e = 0.001;

module Trapezium(W1, W2, D, H) {
  linear_extrude(height = H) {
    polygon(points = [
      [ W1 / 2, -D / 2 ],
      [ W2 / 2, D / 2 ],
      [ -W2 / 2, D / 2 ],
      [ -W1 / 2, -D / 2 ],
    ]);
  }
}

W1 = 5;
W2 = 8.5;
D = 8.5;
H = 5;
Txy = 1.5;
Tz1 = 1.2;
Tz2 = 1.7;

S1 = 3;
S2 = 2;

difference() {
  Trapezium(W1 = W1, W2 = W2, D = D, H = H);
  translate([ 0, Txy / 2, Tz1 ]) {
    Trapezium(W1 = W1 - 2 * Txy, W2 = W2 - 2 * Txy, D = D, H = H - Tz1 - Tz2);
  }
  translate([ 0, 0, 2 + Tz1 ]) {
    difference() {
      translate([ 0, Txy / 2, 0 ]) {
        Trapezium(W1 = W1 - 2 * Txy, W2 = W2 - 2 * Txy, D = D,
                  H = H - Tz1 - Tz2);
      }
      translate([ -5, -10, -5 ]) { cube(10); }
    }
  }
  translate([ 0, 1, H / 2 ]) {
    cube(
        [
          10,
          S1,
          S2,
        ],
        center = true);
  }
}