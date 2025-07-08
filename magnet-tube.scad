$fn = 120;
e = 0.01;

L = 65;      // Length of the cylinder
T = 1;       // Wall thickness
ID = 18;     // Inner diameter
OD = ID + T; // Outer diameter

difference() {
    union() {
        // Main cylinder
        cylinder(h=L, d=OD);

        // Chamfered barrier
        d = OD - e;
        translate([0, 0, 50]) {
            cylinder(h=5, d1=d, d2=d + 5);
            translate([0, 0, 5])
                cylinder(h=5, d=d + 5);
            translate([0, 0, 10])
                cylinder(h=1, d1=d + 5, d2=d);
        }
    }

    // Inner cylinder cavity
    translate([0, 0, T])
        cylinder(h=L, d=ID);
}
