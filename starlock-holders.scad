include <BOSL2/std.scad>;

$fn = 60;
e = 0.001;

rail_l = 175;
rail_w = 12.6;
rail_h = 3.5;

stem_h = 30;
stem_d = 9.5;
stem_spacing = 3*25.4;

tab_w = 15;
tab_t = 2;
tab_h = stem_h - 5;

rounding = 0.8;


module holder(rail_l, range, holes) {
    difference() {
        cube([rail_l, rail_w, rail_h], center=true);
        for (x = holes) {
            translate([x, 0, -rail_h/2-e]) {
                h = rail_h + 2*e;
                cylinder(d1=3, d2=3+2*h, h=h, $fn=20);
            }
        }
    }
    for (i = range) {
        translate([i * stem_spacing, 0, 0]) {
            minkowski() {
                cylinder(d=stem_d-2*rounding, h=stem_h-rounding);
                sphere(r=rounding);
            }
            translate([0, 0, tab_h/2]) {
                cuboid([tab_w, tab_t, tab_h], rounding=rounding, anchor=CENTER, $fn=20);
            }
        }
    }
}

test = false;

if (test) {
    translate([0, -2*rail_w, 0])
        holder(rail_l - 2*stem_spacing, [0]);
} else {
    for (j = [0:1]) {
        translate([0, j * 2*rail_w, 0]) {
            x = rail_l/2 - 30;
            holder(rail_l, [-1:1], [-x, x]);
        }
    }

    for (j = [2:3]) {
        l = rail_l + stem_spacing;
        translate([0, j * 2*rail_w, 0]) {
            x = l/2 - 30;
            holder(l, [-1.5:1.5], [-x, 0, x]);
        }
    }
}
