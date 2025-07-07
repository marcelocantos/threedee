$fn=30;
e = 0.01;

for (i = [0:0]) {
    for (j = [0:1]) {
        for (k = [0:6]) {
            translate([i * 26 + j * 12, k * 12, 0]) {
                difference() {
                    cylinder(d=10, h=20, center=true);
                    translate([0, 0, -e]) {
                        cylinder(d=4.5, h=20+3*e, center=true);
                    }
                }
            }
        }
    }
}