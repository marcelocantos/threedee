$fn = 30;
e = 0.001; // epsilon

module baby_gate_latch(span) {
  margin = 2;

  span = span + margin;

  //----------------------------------------------------------------
  // base

  // screw hole dimensions
  r1 = 4.5 / 2;
  r2 = 9 / 2;
  bevel = 2;

  // base dimensions
  base_thickness = 10;
  base_length = 40;

  difference() {
    cube([ base_thickness, base_length, width ]);
    for (i = [ 2, 5 ]) {
      h = base_thickness + 2 * e;
      translate([ -e, 2 + i * base_length / 7, width / 2 ])
          rotate(a = 90, v = [ 0, 1, 0 ]) rotate_extrude() polygon([
            [ 0, 0 ],
            [ r1, 0 ],
            [ r1, h - (r2 - r1) ],
            [ r2, h ],
            [ 0, h ],
          ]);
    }
  }

  //----------------------------------------------------------------
  // stem and arrow

  // arrow dimensions
  arrowhead_width = 8;
  arrowhead_length = 11.5;
  tip = 0.5;
  arrow_bevel = 1;

  // stem dimensions
  width = 10;
  inner = span;
  outer = span + arrowhead_length;
  thickness = 3;

  intersection() {
    linear_extrude(height = width) {
      polygon([
        [ 0, 0 ],
        [ outer, 0 ],
        [ outer, tip ],
        [ outer - arrow_bevel, tip + arrow_bevel ],
        [ inner, arrowhead_width ],
        [ inner, thickness ],
        [ 0, thickness ],
      ]);
    }
    union() {
      cube([ outer - width / 2, arrowhead_width, base_thickness ]);
      translate([ outer - width / 2, 0, width / 2 ]) rotate(90, [ -1, 0, 0 ]) {
        cylinder(h = arrowhead_width, r = width / 2);
      }
    }
  }
}

baby_gate_latch(span = 86.5);
translate([ 0, 60, 0 ]) { baby_gate_latch(span = 100); }