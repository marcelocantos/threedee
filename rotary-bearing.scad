$fn = 30;
e = 0.001;

bearing_id = 4.72;
bearing_od = 12.7;
bearing_h = 8;

module screw_holes(diam, dist, h) {
    for (a = [1, 3, 5, 7]) {
        rotate(45*a)
            translate([-(dist+diam)/2, 0, 0])
                cylinder(d1=diam+0.1, d2=0, h=h);
    }
}

module bearing_holds(center_hole_diam, thickness, adjust) {
    for (a = [0:2]) {
        rotate(120*a)
            translate([bearing_od/2 - center_hole_diam/2 - adjust, 0, thickness-e]) {
                cylinder(d=bearing_id+0.1, h=bearing_h - 2);
                cylinder(d=(bearing_id+bearing_od)/2, h=1);
            }
    }
}

module base_plate(
    size,
    h,
    corner_radius,
    center_hole_diam,
    bearing_adjust,
    screw_hole_1_diam=0,
    screw_hole_1_dist,
    screw_hole_2_diam=0,
    screw_hole_2_dist,
    thickness=1.4,
    buffer=1,
    crosshairs=false,
    bearings=false,
) {
    t = thickness;
    hw = (size+0.6)/2-corner_radius;
    radius = sqrt(2)*(hw) + corner_radius;
    difference() {
        // Main plate
        cylinder(h = 3*t, r = radius + buffer, $fn = 240);

        // Recess
        translate([-hw, -hw, 2*t]) {
            minkowski() {
                cube([2*hw, 2*hw, t+e]);
                cylinder(h = e, r = corner_radius, $fn=60);
            }
        }
        translate([0, 0, t]) {
            cylinder(h = t + e, r = radius, $fn=240);
            cylinder(h = 2*t + e, r = radius-2*buffer, $fn=240);
        }
        if (screw_hole_1_diam > 0) {
            // Screw holes
            translate([0, 0, -e]) {
                screw_holes(screw_hole_1_diam, screw_hole_1_dist, t+2*e);
            }
        }

        // Center crosshairs
        if (crosshairs) {
            translate([0, 0, -e]) {
                difference() {
                    cylinder(h = t/4 + 2*e, r = 10, $fn = 90);
                    for (angle = [0, 180]) {
                        rotate([0, 0, angle])
                            translate([e, e, 0])
                                cube([11, 11, 10]);
                    }
                }
            }
        }
    }

    // Pins
    if (screw_hole_2_diam > 0)
        translate([0, 0, t-e])
            rotate(-5)
                screw_holes(screw_hole_2_diam, screw_hole_2_dist, 1);

    if (bearings) {
        bearing_holds(center_hole_diam, t, bearing_adjust);
    }
}

// base_plate(
//     size=76.43,
//     h=8,
//     corner_radius=8,
//     center_hole_diam=34.3,
//     bearing_adjust=0.15,
//     screw_hole_1_diam=4,
//     screw_hole_1_dist=88.2,
//     screw_hole_2_diam=2.4,
//     screw_hole_2_dist=74.2
// );

base_plate(
    size=153,
    h=9,
    corner_radius=5,
    center_hole_diam=120,
    bearing_adjust=0.35,
    // screw_hole_1_diam=6.9,
    // screw_hole_1_dist=194.6,
    screw_hole_2_diam=2,
    screw_hole_2_dist=184.8,
    buffer=2,
    bearings=true
);

// base_plate(
//     size=153.5,
//     h=9,
//     corner_radius=5,
//     center_hole_diam=120,
//     bearing_adjust=0.27,
//     // screw_hole_1_diam=6.9,
//     // screw_hole_1_dist=194.6,
//     // screw_hole_2_diam=2.4,
//     // screw_hole_2_dist=184.8
//     buffer=2,
//     crosshairs=true
// );
