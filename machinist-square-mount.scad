include <BOSL2/std.scad>

e = 0.001;

module square(lh, wh, th, lb, wb, tb, xb, zb, g) {
    g2 = 2*g;
    translate([0, 0, zb+g])
        cube([th+g2, wh+g2, lh+g2]);
    translate([xb, 0, 0])
        cube([tb+g2, lb+g2, wb+g2]);
}

t1 = 9.44;
t2 = 9.57;
t3 = 11.54;

h = 50;

module squares(g) {
    x0 = 15;
    z = 5;
    translate([x0, 0, z])
        square(45.14, 18.8, t1, 71.6, 18.81, 1.96, 3.98, 5.09, g);

    x1 = x0 + 20 + (t1 + t2)/2;
    translate([x1, 0, z])
        square(69.81, 19.30, t2, 121.31, 18.85, 2.06, 3.57, 4.97, g);

    x2 = x1 + 20 + (t2 + t3)/2;
    translate([x2, 0, z])
        square(100.43, 25.07, t3, 178.40, 24.06, 1.81, 4.49, 5.55, g);
}

difference() {
    translate([100/2, 50/2+15, 0]) {
        offset_sweep(rect([100, h], rounding=6), 35, top=os_circle(r=6));
    }

    squares(0.3);

    hole_d = 5; // Diameter of screw holes
    hole_offset_x = 32; // Distance from left edge for first hole
    hole_spacing = 35; // Distance between holes
    hole_depth = 45; // From top to 10mm from bottom

    for(i = [0:1]) {
        translate([hole_offset_x + i * hole_spacing, 25+15, -e]) {
            cylinder(d=5, h=h+2*e);
            translate([0, 0, 5])
                cylinder(d=12, h=h);
        }
    }
}

// color("#0000ff40")
//     squares(0);
