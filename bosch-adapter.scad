$fn = 720 / 3;

// Small deltas
d = 0.001;
d2 = 2 * d;

// Extrusion thickness for a 0.4mm nozzle
t = 0.2;

hmid = 15;
hhi = 25 - t;
hmez = 21.22;

rilo = 46.38 / 2 - t;
rolo = 48.36 / 2 - t;
rimid = 45.54 / 2 - t;
romid = 47.31 / 2 - t;
rihi = rilo + (rimid - rilo) / hmid * hhi;

rslotmid = 46.2 / 2;
hslotmid = 11.26;
hslothi = 21.42;

r3lo = 35.65 / 2 + t / 2;
r3hi = 35 / 2 + t / 2;
h3lo = 3.3;

chordmid = 11.15;
chordlo = 13.5;

chord3lo = 14.25;
chord3mid = 10.58;
chord3hi = 8.15;

translate([ 0, 0, hhi ]) rotate(180, [ 1, 0, 0 ]) {
  // Main cylinder
  difference() {
    cylinder(hhi, rilo + d, rimid + d);
    translate([ 0, 0, -d ]) cylinder(hhi + d2, r3lo, r3hi);
    translate([ 0, 0, -d2 ]) cylinder(rilo / 1.5, rilo, 0);
  }

  // Primary slots
  intersection() {
    difference() {
      cylinder(hmid, rolo, romid);
      translate([ 0, 0, -d ]) cylinder(hmid + d2, rilo, rimid);
    }
    for (i = [1:3]) {
      rotate(45 * i, [ 0, 0, 1 ]) {
        rotate(90, [ 1, 0, 0 ]) {
          translate([ 0, 0, -rolo ]) {
            linear_extrude(height = 2 * rolo) polygon(points = [
              [ chordlo / 2, 0 ],
              [ -chordlo / 2, 0 ],
              [ -chordmid / 2, hmid ],
              [ chordmid / 2, hmid ],
            ]);
          }
        }
      }
    }
  }

  // Tab slots
  intersection() {
    difference() {
      cylinder(hslotmid, rolo, rslotmid);
      translate([ 0, 0, -d ]) cylinder(hslotmid + d2, rilo, rslotmid - t);
    }
    rotate(90, [ 1, 0, 0 ]) {
      translate([ 0, 0, -rolo ]) {
        linear_extrude(height = 2 * rolo) polygon(points = [
          [ chordlo / 2, 0 ],
          [ -chordlo / 2, 0 ],
          [ -chordmid / 2, hmid ],
          [ chordmid / 2, hmid ],
        ]);
      }
    }
  }

  // Snap tabs
  dot = 2;
  for (i = [0:1]) {
    rotate(180 * i, [ 0, 0, 1 ]) {
      translate([ 0, -rslotmid - 0.3, hslotmid + dot ])
          rotate(-90, [ 1, 0, 0 ]) {
        scale([ 2, 1, 0.2 ]) {
          sphere(dot);
          cylinder(h = 3 * dot, r = dot);
        }
      }
    }
  }
}