include <gears.scad>;

m = 3 / 2;
w = 20 / 2;
b = 0.5 / 2;

translate(v = [ 0, 0, 0 ]) {
  difference() {
    union() {
      bevel_gear(modul = m,               // Modulus
                 tooth_number = 20,       // Teeth count
                 partial_cone_angle = 45, // Pressure angle
                 tooth_width = w,         // Helix angle
                 bore = b                 // Tooth thickness
      );
      translate([ 0, 0, -2.7 ]) { cylinder(h = 3, d = 14.95); }
    }
    translate([ 0, 0, -3 ]) {
      cylinder(h = 24, d = 10 * (2 / sqrt(3)) - 0.2, $fn = 6);
    }
  }
}
translate(v = [ 3.5 * w, 0, 0 ]) {
  difference() {
    union() {
      bevel_gear(modul = m,               // Modulus
                 tooth_number = 20,       // Teeth count
                 partial_cone_angle = 45, // Pressure angle
                 tooth_width = w,         // Helix angle
                 bore = b                 // Tooth thickness
      );
      translate([ 0, 0, -2.7 ]) { cylinder(h = 3, d = 14.95); }
    }
    translate([ 0, 0, -3 ]) { cylinder(h = 24, d = 10 + 0.4); }
  }
}