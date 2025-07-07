$fn = 60;
e = 0.001;
e2 = 2*e;

dropR = 0.4;

module drop(r=dropR) {
    sphere(r=r, $fn=12);
}

module rpi4b_box(length, width, buffer, height, wall, margin) {
    standoff_h = 3;
    standoff_d = 6;
    hole_d = 2.7;

   // Standoffs (RPi 4B mounting holes: 58mm x 49mm rectangle, 3mm holes)
    hole_margin = 2.2;
    inset = buffer + hole_margin + hole_d/2;
    right = inset + 58;
    top = inset + 49;

    // Main box
    difference() {
        // -0.5 thins out the walls to make room for USB/RJ45 ports
        cam = 26;
        translate([-cam, 0, 0]) {
            minkowski() {
                cube([length-0.5+cam, width, height]);
                drop();
            }
        }
        translate([wall-8, wall, wall])
            cube([length-2*wall+8, width-2*wall, height]);

        // Side ports cutout
        translate([inset+2.5, -1, wall+2.5]) {
            // USB ports
            cube([58-6, 13.5+e2, 8.5]);
        }
    }

    for (x = [inset, right]) {
        for (y = [inset, top]) {
            translate([x, y, wall-e]) {
                difference() {
                    cylinder(h=standoff_h, d=standoff_d);
                    translate([0,0,-e])
                        cylinder(h=standoff_h+e2, d=hole_d);
                }
            }
        }
    }
}

wall = 2;
margin = 0.5;
rpiL = 85.6; // RPi 4B length
rpiW = 56.5; // RPi 4B width
buffer = wall + margin; // Buffer around the RPi
boxL = rpiL + 2*buffer; // Total length of the box
boxW = rpiW + 2*buffer; // Total width of the box
boxH = 30;

difference() {
    echo("Length: ", boxL, " Width: ", boxW, " Buffer: ", buffer, " Height: ", boxH, " Wall: ", wall, " Margin: ", margin);

    union() {
        rpi4b_box(boxL, boxW, buffer, boxH, wall, margin);
        translate([-1, boxW/2, boxH/2]) {
            rotate([0, 90, 0]) {
                translate([10.3, 0.75, -9]) cylinder(h=6, d=4);
                translate([-10.3, 0.75, -9]) cylinder(h=6, d=4);
            }
        }
    }

    translate([-3, boxW/2, boxH/2]) {
        // Mirror mount slot
        translate([-23-dropR, 0, 0]) {
            rotate([90, 45, 0]) {
                cube([18, 18, boxW+2*dropR], center=true);
            }
        }

        rotate([0, 90, 0]) {
            // Camera tubes
            translate([0, 0, -7.5+e2]) {
                cylinder(h=7, d1=10.5, d2=7.7, center=true);
            }
            translate([0, 0, -3.5+e]) {
                cube([9, 9, 1], center=true);
            }
            translate([10.3, 0.75, -9]) cylinder(h=8+e, d=1.5);
            translate([-10.3, 0.75, -9]) cylinder(h=8+e, d=1.5);
        }
        translate([-17, 0, 0]) {
            cube([14, 10.5, boxW+2*dropR], center=true);
        }
    }

    // camera_w = boxW;
    // translate([-20, boxW/2-camera_w/2, 0]) {
    //     cube([20, camera_w, boxH-wall]);
    // }

    // USB socket #1 cutout
    usb1Y = buffer + 2.3;
    usb1W = 13.5;
    translate([boxL-wall-e, usb1Y, 7.6]) {
        cube([wall+e2, usb1W, boxH]);
    }

    // USB socket #2 cutout
    usb2Y = buffer + 20.7;
    usb2W = usb1W;
    translate([boxL-wall-e, usb2Y, 7.6]) {
        cube([wall+e2, usb2W, boxH]);
    }

    // Ethernet socket cutout
    rj45_y = buffer + 37.65;
    rj45_w = 16.2;
    translate([boxL-wall-e, rj45_y, 7]) {
        cube([wall+e2, rj45_w, boxH]);
    }
}
