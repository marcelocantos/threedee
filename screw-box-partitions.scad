include <BOSL2/std.scad>

$fn = 30;
e = 0.001;

h = 41;
w = 49;
r = 0.5;

// grid_copies(spacing=[h+5, w+5], n=[3, 4])
difference() {
    union() {
        h = h - 2*r;
        translate([r, 0, 0])
            linear_extrude(1.4)
                polygon([[0, 0], [h, 0.5], [h, w-0.5], [0, w]]);
        r2 = 0.7;
        translate([r2, 0, r2])
            rotate(-90, [1, 0, 0])
                cylinder(h = w, r = r2);
    }

    // chamfer
    c = 5;
    translate([h, r, -e])
        rotate([0, 0, 45])
            cube([c, c, 4], center=true);
    translate([h, w-r, -e])
        rotate([0, 0, 45])
            cube([c, c, 4], center=true);

    // recessed area
    translate([2.5, 2, 0.8]) {
        linear_extrude(1.4) {
            h = h - 5;
            w = w - 4;
            minkowski() {
                polygon([[0, 0], [h, 0.5], [h, w-0.5], [0, w]]);
            }
        }
    }

    // holes
    translate([h/2, w/2, -e]) {
        grid_copies(spacing=4, n=[9, 11]) {
            cylinder(d=2.5, h=1);
        }
    }
}